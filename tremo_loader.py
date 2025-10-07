import argparse

import serial
import os
import sys
import time
import struct
import zlib
import binascii
import serial.tools.list_ports as list_ports

VERSAO_GRAVADOR = "101"
BAUD_DEFAULT = 921600
TIMEOUT_DEFAULT = 2
EEPROM_ENDERECO = 0x0801F000  # Endereço inicial da eeprom emulada na flash
EEPROM_SIZE = 512  # Tamanho da eeprom emulada na flash

CMD_SYNC = 1
CMD_JUMP = 2
CMD_FLASH = 3
CMD_ERASE = 4
CMD_VERIFY = 5
CMD_WROTP = 6
CMD_RDOTP = 7
CMD_WROPT0 = 8
CMD_RDOPT0 = 9
CMD_WROPT1 = 10
CMD_RDOPT1 = 11
CMD_REBOOT = 12
CMD_SN = 13
CMD_WRREG = 14
CMD_RDREG = 15
CMD_BAUDRATE = 16
CMD_VERSION = 17
CMD_PORT = 18

lista_portas_disponiveis = []
verbose: bool = False
com_timeout = 2
apaga_eeprom: bool = True

### @brief Classe para comunicação com o bootloader do Tremo
class TremoLoader(object):
    def __init__(self):
        self.ser = None

    ## @brief Verifica se o canal serial está sincronizado e o ASR está respondendo.
    ## @return None
    ## @exception CmdException: se o sync falhar
    def sync(self):
        self.enviar_cmd(CMD_SYNC)
        self.aguardar_resposta()

    ## @brief Desvia a execução do código para o endereço especificado.
    ##   Usado para iniciar o firmware de aplicação após gravação.
    ## @param  addr: (4 bytes) endereço para onde o jump deve ser feito
    ## @return None
    ## @exception CmdException: se o jump falhar
    def jump(self, addr):
        self.enviar_cmd(CMD_JUMP, struct.pack('<I', addr))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: falha no jump")

    ## @brief Grava o conteúdo do arquivo na flash
    ## @param  addr: (4 bytes) endereço inicial da flash a ser gravada
    ## @param  arquivo_bin: (n bytes) conteúdo do arquivo
    ## @return None
    ## @exception CmdException: se a gravação falhar
    def flash(self, addr, arquivo_bin):
        arq_len = len(arquivo_bin)  # uint32
        self.enviar_cmd(CMD_FLASH, struct.pack('<II', addr, arq_len) + arquivo_bin)
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: falha ao gravar a flash")

    ## @brief Apaga uma área da flash
    ## @param  addr: (4 bytes) endereço inicial da flash a ser apagada
    ## @param  size: (4 bytes) tamanho em bytes a ser apagado
    ## @return None
    ## @exception CmdException: se o apagamento falhar
    def erase(self, addr, size):
        self.enviar_cmd(CMD_ERASE, struct.pack('<II', addr, size))
        ret, _ = self.aguardar_resposta()

        if verbose:
            print('Apagando %d bytes em %s...' % (size, hex(addr)))

        if ret != 0:
            raise CmdExcessao("ERROR: falha ao apagar a flash")

    ## @brief Verifica se o conteúdo da flash é igual ao do arquivo
    ##   Calcula o checksum da Flash em uma região e compara com o CRC informado.
    ## @param  addr: (4 bytes) endereço inicial da flash a ser verificada
    ## @param  size: (4 bytes) tamanho em bytes a ser verificado
    ## @param  checksum: (4 bytes) checksum crc32 do arquivo
    ## @return None
    ## @exception CmdException: se a verificação falhar
    def verify(self, addr, size, checksum):
        self.enviar_cmd(CMD_VERIFY, struct.pack('<III', addr, size, checksum))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: flash diferente do arquivo")

    ## @brief Escreve na área OTP (One-Time Programmable) da flash
    ##   Cada bit só pode ser programado uma vez (1→0).
    ## @param:  addr: (4 bytes) endereço inicial da OTP a ser escrita
    ## @param:  buffer: (n bytes) dados a serem escritos
    ## @return None
    ## @exception CmdException: se a gravação falhar
    ## @note: essa operação é irreversível — não há ERASE para OTP.
    def escrever_otp(self, addr, buffer):
        buf_len = len(buffer)
        self.enviar_cmd(CMD_WROTP, struct.pack('<II', addr, buf_len) + buffer)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_otp")

    ## @brief Lê a área OTP da flash
    ## @param  addr: (4 bytes) endereço inicial da OTP a ser lida
    ## @param  size: (4 bytes) tamanho em bytes a ser lido
    ## @return dados lidos (n bytes)
    ## @exception CmdException: se a leitura falhar
    def ler_otp(self, addr, size):
        self.enviar_cmd(CMD_RDOTP, struct.pack('<II', addr, size))
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_otp")
        return rsp

    ## @brief Grava o registrador Option0, que controla bits de configuração de boot e segurança.
    ## @param  opt0_l: (4 bytes) valor msb a ser escrito
    ## @param  opt0_h: (4 bytes) valor lsb a ser escrito
    ## @return None
    ## @exception CmdException: se a gravação falhar
    def escrever_opt0(self, opt0_l, opt0_h):
        buf = struct.pack('<II', opt0_l, opt0_h)
        self.enviar_cmd(CMD_WROPT0, buf)
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_opt0")

    ## @brief Lê o registrador de configuração Option0.
    ## @return opt0_l (4 bytes) e opt0_h (4 bytes)
    ## @exception CmdException: se a leitura falhar
    def ler_opt0(self):
        self.enviar_cmd(CMD_RDOPT0)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_opt0")
        opt0_l, opt0_h = struct.unpack('<II', rsp)
        return opt0_l, opt0_h

    ## @brief Grava o registrador Option1, com parâmetros adicionais de boot.
    ## @param  opt0_l: (4 bytes) valor msb a ser escrito
    ## @param  opt0_h: (4 bytes) valor lsb a ser escrito
    ## @return None
    ## @exception CmdException: se a gravação falhar
    def escrever_opt1(self, opt1_l, opt1_h):
        buf = struct.pack('<II', opt1_l, opt1_h)
        self.enviar_cmd(CMD_WROPT1, buf)
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_opt1")

    ## @brief Lê o registrador de configuração Option1.
    ## @return opt1_l (4 bytes) e opt1_h (4 bytes)
    ## @exception CmdException: se a leitura falhar
    def ler_opt1(self):
        self.enviar_cmd(CMD_RDOPT1)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_opt1")
        opt1_l, opt1_h = struct.unpack('<II', rsp)
        return opt1_l, opt1_h

    ## @brief Reinicia o dispositivo via software (mesmo que apertar o botão reset)
    ##   Usado para sair do modo bootloader e executar o firmware.
    ## @param  mode: 0 - reset normal,
    ##               1 - reset para modo de bootloader
    ## @return None
    ## @exception CmdException: se o reset falhar
    def sw_reset(self, mode=0):
        self.enviar_cmd(CMD_REBOOT, struct.pack('B', mode))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel reiniciar")

    ## @brief Reinicia o dispositivo via hardware (mesmo que apertar o botão reset)
    ## @param  mode: 0 - reset normal,
    ##               1 - reset para modo de bootloader
    ## @return None
    ## @exception CmdException: se o reset falhar
    def hw_reset(self, mode=0):
        if mode:
            self.ser.setDTR(True)  # gpio2 1
            self.ser.setRTS(True)  # rst 0
            time.sleep(0.1)
            self.ser.setRTS(False)  # rst 1
            time.sleep(0.1)
            self.ser.setDTR(False)  # gpio2 0
        else:
            self.ser.setRTS(True)  # rst 0
            time.sleep(0.1)
            self.ser.setRTS(False)  # rst 1

    ## @brief Lê o serial do ASR
    ## @return serial lido (8 bytes)
    ## @exception CmdException: se a leitura falhar
    def serial_asr(self):
        self.enviar_cmd(CMD_SN)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: falha na leitura do serial")
        return rsp

    ## @brief Escreve um valor em um registrador
    ## @param  addr: (4 bytes) endereço do registrador a ser escrito
    ## @param  valor: (4 bytes) valor a ser escrito
    ## @return None
    ## @exception CmdException: se a escrita falhar
    def escrever_reg(self, addr, valor):
        self.enviar_cmd(CMD_WRREG, struct.pack('<II', addr, valor))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_reg")

    ## @brief Lê o conteúdo de um registrador
    ## @param  addr: endereço do registrador a ser lido
    ## @return valor lido (4 bytes)
    ## @exception CmdException: se a leitura falhar
    def ler_reg(self, addr):
        self.enviar_cmd(CMD_RDREG, struct.pack('<I', addr))
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_reg")
        return struct.unpack('<I', rsp)

    ## @brief Altera dinamicamente o baud rate da UART.
    ## @param  baud: (4 bytes) novo baudrate
    ## @return None
    ## @exception CmdException: se a alteração falhar
    def set_baudrate(self, baud):
        self.enviar_cmd(CMD_BAUDRATE, struct.pack('<I', baud))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel alterar o baud")

        try:
            print("baud", baud)
            self.ser.baudrate = baud
        except IOError:
            raise CmdExcessao("ERROR: nao foi possivel alterar o baud")

    ## @biref Seta a porta serial a ser usada
    ## @param  port: nome da porta serial
    ## @param  baud: baudrate da serial
    ## @return None
    ## @exception serial.SerialException: se a porta não puder ser aberta
    def set_port(self, port, baud=BAUD_DEFAULT):
        self.ser = serial.Serial(port, baud, timeout=com_timeout)

    ## @brief Lê a versão do bootloader interno
    ## @return versão lida (4 bytes)
    ## @exception CmdException: se a leitura falhar
    def versao_bootloader(self):
        self.enviar_cmd(CMD_VERSION)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel ler a versao do bootloader")
        return struct.unpack('<I', rsp)

    ## @brief Conecta ao dispositivo
    ## @param  retentativas: número de tentativas de conexão
    ## @return None
    ## @exception CmdException: se a conexão falhar
    def conectar(self, retentativas=3):
        print('Conectando em %s...' % self.ser.port)
        sys.stdout.flush()
        last_error = None

        for _ in range(retentativas):
            try:
                self.hw_reset(1)

                last_error = None
                self.ser.flushInput()
                self.ser.flushOutput()
                self.sync()
                break
            except CmdExcessao as excessao:
                sys.stdout.flush()
                time.sleep(0.05)
                last_error = excessao

        if last_error is not None:
            self.ser.close()
            print('Falha na conexao')
            raise CmdExcessao('Erro de conexao: %s' % last_error)
        print('Conectado. ', end='')
        if verbose:
            print("\n")

    ## @brief Envia um comando ao dispositivo
    ## @param  cmd: comando a ser enviado
    ## @param  buf: dados adicionais do comando
    ## @return None
    ## @exception serial.SerialException: se a escrita falhar
    def enviar_cmd(self, cmd, buf=b""):
        pkt = struct.pack(b'<BBH', 0xFE, cmd, len(buf)) + buf
        checksum = zlib.crc32(pkt) & 0xFFFFFFFF
        pkt += struct.pack(b'<IB', checksum, 0xEF)

        if verbose:
            print(f'Tx[{len(pkt)}]:', binascii.hexlify(pkt))

        self.ser.flushInput()
        self.ser.write(pkt)

    ## @brief Aguarda a resposta do dispositivo
    ## @return (status, dados)
    ##            status: 0 - sucesso, diferente de 0 - erro
    ##            dados: dados adicionais retornados pelo dispositivo
    ##         timeout: tempo máximo de espera pela resposta
    ## @exception CmdException: erro na comunicação ou resposta inválida
    def aguardar_resposta(self):
        header = self.ser.read(4)
        if header == b'':
            raise CmdExcessao("ERROR: timeout leitura do header response")
        (start, status, rsp_data_len) = struct.unpack('<BBH', header)
        if start != 0xFE:
            raise CmdExcessao("ERROR: pacote de resposta errado")
        if rsp_data_len > 512:
            raise CmdExcessao("ERROR: tamanho do pacote de resposta errado")

        remain_data = self.ser.read(rsp_data_len + 5)
        if remain_data == b'':
            raise CmdExcessao("ERROR: timeout leitura de dados")

        pkt = header + remain_data

        if verbose:
            print(f'Rx[{len(pkt)}]:', binascii.hexlify(pkt))

        (crc, end) = struct.unpack('<IB', pkt[4 + rsp_data_len:])

        if end != 0xEF:
            raise CmdExcessao("ERROR: pacote de resposta errado")

        checksum = zlib.crc32(pkt[:4 + rsp_data_len]) & 0xFFFFFFFF
        if crc != checksum:
            raise CmdExcessao("ERROR: CRC errado")

        return status, pkt[4:4 + rsp_data_len]


### @brief Exceção para erros de comando
class CmdExcessao(Exception):
    pass


### @brief Converte um argumento para int, aceitando decimal e hexadecimal
### @param  x: argumento a ser convertido
### @return valor convertido
### @exception ValueError: se o argumento não for um número válido
def arg_int(x):
    return int(x, 0)


### @brief Calcula o CRC32 de um pacote
### @param  pacote: pacote no arquivo
### @return valor do CRC32
### @exception IOError: se o arquivo não puder ser lido
def get_crc32(pacote):
    with open(pacote, 'rb') as f:
        return zlib.crc32(f.read()) & 0xFFFFFFFF


### @brief Tenta conectar em um processador em uma lista de portas disponíveis
### @param  processador: objeto TremoLoader
### @param  lista_portas: lista de portas seriais
### @return True se a conexão for bem sucedida, False caso contrário
### @exception Exception: se ocorrer algum erro
def tremo_conectar(processador, lista_portas, baud):
    for porta in reversed(lista_portas):
        print("Serial port %s" % porta)
        try:
            processador.set_port(porta)
            processador.conectar()
            processador.set_baudrate(baud)
            return True
        except Exception as excessao:
            print("Nao foi possivel conectar em %s: %s" % (porta, excessao))
    return False


### @brief Apaga uma área da flash
### @param  address: endereço inicial da flash a ser apagada
###         size: tamanho em bytes a ser apagado
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_erase(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    processador.erase(param.address, param.size)
    processador.sw_reset(0)


### @brief Apaga a eeprom emulada
### @param  processador: objeto TremoLoader já conectado
### @return None
def apagar_eeprom(processador):
    processador.erase(EEPROM_ENDERECO, EEPROM_SIZE)


### @brief Conecta ao dispositovo e apaga a eeprom emulada
### @param  param: parâmetros do comando
### @param  processador: objeto TremoLoader já conectado
### @return None
def tremo_clean_eeprom(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    apagar_eeprom(processador)
    processador.sw_reset(0)


### @brief Apaga e grava a flash
### @param  param: lista com pares de endereco e nome do arquivo
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_flash(param, processador):
    arquivo = []
    for i in range(0, len(param.addr_file), 2):
        try:
            endereco = int(param.addr_file[i], 0)
        except Exception:
            raise Exception('ERROR: o endereco "%s" deve ser um numero' % param.addr_file[i])

        if not os.access(param.addr_file[i + 1], os.R_OK):
            raise Exception('ERROR: falha na leitura do arquivo: %s' % param.addr_file[i + 1])
        arquivo.append((endereco, param.addr_file[i + 1]))

    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return

    if apaga_eeprom:
        apagar_eeprom(processador)

    for endereco, pacote in arquivo:
        pacote_len = os.path.getsize(pacote)
        crc_pacote = get_crc32(pacote)
        processador.erase(endereco, pacote_len)

        endereco_na_flash = endereco

        if verbose:
            print('Gravando', f' {pacote} no endereco {hex(endereco)}...')
        else:
            print('Gravando', end='', flush=True)

        with open(pacote, 'rb') as f:
            l = 0
            while True:
                line_data = f.read(512)
                if line_data == b'':
                    break

                processador.flash(endereco_na_flash, line_data)
                endereco_na_flash += len(line_data)
                l += len(line_data)
                if not verbose:
                    print('.', end='', flush=True)
        processador.verify(endereco, pacote_len, crc_pacote)

    if not verbose:
        print('.')

    processador.sw_reset(0)


### @brief Escreve em uma área da otp da flash
### @param  param: endereço inicial da otp a ser escrita
###         data: dados a serem escritos (hexadecimal)
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_escrever_otp(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    processador.escrever_otp(param.address, binascii.unhexlify(param.data))


### @brief Lê a área da otp da flash
### @param  address: endereço inicial da otp a ser lida
###         size: tamanho em bytes a ser lido
### @param  processador: objeto TremoLoader já conectado
### @return dados lidos
### @exception Exception: se ocorrer algum erro
def tremo_ler_otp(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return b''
    return processador.ler_otp(param.address, param.size)


### @brief Escreve na área otp0 da flash
### @param  opt0_l: valor msb a ser escrito
###         opt0_h: valor lsb a ser escrito
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_escrever_otp0(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    processador.escrever_opt0(param.opt0_l, param.opt0_h)


### @brief Lê a área otp0 da flash
### @param  param: parâmetros do comando
### @param  processador: objeto TremoLoader já conectado
### @return (opt0_l, opt0_h)
### @exception Exception: se ocorrer algum erro
def tremo_ler_otp0(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt0()


### @brief Escreve na área otp1 da flash
### @param  opt1_l: valor msb a ser escrito
###         opt1_h: valor lsb a ser escrito
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_escrever_otp1(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    processador.escrever_opt1(param.opt1_l, param.opt1_h)


### @brief Lê a área otp1 da flash
### @param  param: parâmetros do comando
### @param  processador: objeto TremoLoader já conectado
### @return (opt1_l, opt1_h)
### @exception Exception: se ocorrer algum erro
def tremo_ler_otp1(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt1()


### @brief Lê o serial do ASR
### @param  param: parâmetros do comando
### @param  processador: objeto TremoLoader já conectado
### @return serial lido
### @exception Exception: se ocorrer algum erro
def tremo_serial_asr(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return b''
    return processador.serial_asr()


### @brief Lê o serial do ASR
### @param  param: parâmetros do comando
### @param  processador: objeto TremoLoader já conectado
### @return serial lido
### @exception Exception: se ocorrer algum erro
def tremo_sw_reset(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return b''
    return processador.sw_reset(0)


### @brief Verifica o conteudo da flash
### @param  address: endereço inicial da flash a ser verificada
###         filename: arquivo para comparar com a flash
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_verify(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return

    # Calcula o CRC32 do arquivo
    image_checksum = get_crc32(param.filename)
    image_size = os.path.getsize(param.filename)

    print(f'Verificando {param.filename} no endereco {hex(param.address)}...')
    processador.verify(param.address, image_size, image_checksum)


### @brief Lê a versão do bootloader
### @param  param: parâmetros do comando
### @param  processador: objeto TremoLoader já conectado
### @return versão lida
### @exception Exception: se ocorrer algum erro
def tremo_versao_bootloader(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return (0,)
    return processador.versao_bootloader()


### @brief Lê o conteudo de um registrador
### @param  address: endereço do registrador a ser lido
### @param  processador: objeto TremoLoader já conectado
### @return valor lido
### @exception Exception: se ocorrer algum erro
def tremo_ler_reg(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return (0,)
    return processador.ler_reg(param.address)


### @brief Escreve em um registrador
### @param  address: endereço do registrador a ser escrito
###         value: valor a ser escrito
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_escrever_reg(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    processador.escrever_reg(param.address, param.value)


### @brief Executa um jump para um endereco
### @param  address: endereço para onde o jump deve ser feito
### @param  processador: objeto TremoLoader já conectado
### @return None
### @exception Exception: se ocorrer algum erro
def tremo_jump(param, processador):
    if not tremo_conectar(processador, lista_portas_disponiveis, param.baud):
        return
    processador.jump(param.address)


### @brief Retorna a lista de portas seriais disponíveis
### @return lista de portas seriais
def get_lista_portas_com():
    return sorted(ports.device for ports in list_ports.comports())


### @brief Retorna a porta serial conectada
### @param  lista_portas: lista de portas seriais
### @return porta serial conectada
def get_dispositivo_conectado(lista_portas):
    for each_port in reversed(lista_portas):
        print("Serial port %s" % each_port)


def tremo_print_help(help_parser):
    print("Tremo Loader v%s" % VERSAO_GRAVADOR)
    help_parser.print_help()
    print("\nPortas seriais disponiveis:")
    portas = get_lista_portas_com()
    if len(portas) == 0:
        print("  Nenhuma porta serial encontrada")
    else:
        for porta in portas:
            print(" ", porta)


### @brief Adiciona os argumentos comuns ao parser
### @param  argumentos: parser de argumentos
### @return None
def tremo_add_argumentos(argumentos):
    msg = 'porta serial'
    argumentos.add_argument('--port', '-p', help=msg)

    msg = 'baudrate, default 921600'
    argumentos.add_argument('--baud', '-b', help=msg, type=int, default=BAUD_DEFAULT)

    msg = 'modo verbose para debug'
    argumentos.add_argument('--verbose', '-v', help=msg, action='store_true')

    msg = 'timeout da serial em segundos, default 2s'
    argumentos.add_argument('--timeout', '-t', help=msg, type=int, default=TIMEOUT_DEFAULT)

    msg = 'mantém os dados da eeprom emulada'
    argumentos.add_argument('--eeprom', '-e', help=msg, action='store_true')


### @brief Programa principal
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    tremo_add_argumentos(parser)

    msg_help = 'run tremo_loader.py {command} -h'
    subparsers = parser.add_subparsers(dest='command', help=msg_help)

    # erase
    msg_help = 'apagar determinada area da flash'
    parser_erase = subparsers.add_parser('erase', help=msg_help)

    msg_help = 'endereco da flash a ser apagada'
    parser_erase.add_argument('address', help=msg_help, type=arg_int)

    msg_help = 'quantidade de bytes a serem apagados'
    parser_erase.add_argument('size', help=msg_help, type=arg_int)

    # flash
    msg_help = 'apagar e gravar a flash'
    parser_flash = subparsers.add_parser('flash', help=msg_help)

    msg_help = 'endereco e nome do arquivo, Ex.: 0x08000000 app.bin'
    parser_flash.add_argument('addr_file', metavar='<address> <filename>', help=msg_help, nargs='+')

    # escrever_otp
    msg_help = 'escrever em uma area da opt da flash'
    parser_escrever_otp = subparsers.add_parser('escrever_otp', help=msg_help)

    msg_help = 'endereco flash otp'
    parser_escrever_otp.add_argument('address', help=msg_help, type=arg_int)

    msg_help = 'dado a ser escrito na flash (hexadecimal)'
    parser_escrever_otp.add_argument('data', help=msg_help)

    # ler_otp
    msg_help = 'ler a area da otp da flash'
    parser_ler_otp = subparsers.add_parser('ler_otp', help=msg_help)

    msg_help = 'endereco flash otp'
    parser_ler_otp.add_argument('address', help=msg_help, type=arg_int)

    msg_help = 'endereco flash otp'
    parser_ler_otp.add_argument('size', help=msg_help, type=arg_int)

    # escrever_otp0
    msg_help = 'escrever na area otp0 da flash'
    parser_escrever_otp0 = subparsers.add_parser('escrever_otp0', help=msg_help)

    msg_help = 'valor msb a ser escrito'
    parser_escrever_otp0.add_argument('opt0_l', help=msg_help, type=arg_int)

    msg_help = 'valor lsb a ser escrito'
    parser_escrever_otp0.add_argument('opt0_h', help=msg_help, type=arg_int)

    # ler_otp0
    msg_help = 'ler a area otp0 da flash'
    parser_ler_otp0 = subparsers.add_parser('ler_otp0', help=msg_help)

    # escrever_otp1
    msg_help = 'escrever na area otp1 da flash'
    parser_escrever_otp1 = subparsers.add_parser('escrever_otp1', help=msg_help)

    msg_help = 'valor msb a ser escrito'
    parser_escrever_otp1.add_argument('opt1_l', help=msg_help, type=arg_int)

    msg_help = 'valor lsb a ser escrito'
    parser_escrever_otp1.add_argument('opt1_h', help=msg_help, type=arg_int)

    # ler_otp1
    msg_help = 'ler a area otp1 da flash'
    parser_ler_otp1 = subparsers.add_parser('ler_otp1', help=msg_help)

    # serial
    msg_help = 'ler o serial do ASR'
    parser_serial = subparsers.add_parser('serial', help=msg_help)

    # reset
    msg_help = 'resetar o ASR'
    parser_reset = subparsers.add_parser('reset', help=msg_help)

    # verify
    msg_help = 'verificar o conteudo da flash'
    parser_verify = subparsers.add_parser('verify', help=msg_help)

    msg_help = 'endereco da flash a ser verificado'
    parser_verify.add_argument('address', help=msg_help, type=arg_int)

    msg_help = 'arquivo para comparar com a flash'
    parser_verify.add_argument('filename', help=msg_help)

    # versao_bootloader
    msg_help = 'ler a versao do bootloader'
    parser_versao_bootloader = subparsers.add_parser('versao_bootloader', help=msg_help)

    # ler_reg
    msg_help = 'ler o conteudo de um registrador'
    parser_ler_reg = subparsers.add_parser('ler_reg', help=msg_help)

    msg_help = 'endereco do registrador a ser lido'
    parser_ler_reg.add_argument('address', help=msg_help, type=arg_int)

    # escrever_reg
    msg_help = 'escrever em um registrador'
    parser_escrever_reg = subparsers.add_parser('escrever_reg', help=msg_help)

    msg_help = 'endereco do registrador a ser escrito'
    parser_escrever_reg.add_argument('address', help=msg_help, type=arg_int)

    msg_help = 'valor a ser escrito'
    parser_escrever_reg.add_argument('value', help=msg_help, type=arg_int)

    # jump
    msg_help = 'executar um jump para um endereco'
    parser_jump = subparsers.add_parser('jump', help=msg_help)

    msg_help = 'endereco para onde o jump deve ser feito'
    parser_jump.add_argument('address', help=msg_help, type=arg_int)

    # eeprom
    msg_help = 'limpa a eeprom emulada'
    parser_eeprom = subparsers.add_parser('clear_eeprom', help=msg_help)

    # help
    msg_help = 'mostra essa mensagem de ajuda e sai'
    parser_help = subparsers.add_parser('help', help=msg_help)

    # versão tremo_loader
    msg_help = 'mostra a versao do tremo_loader'
    parser_version = subparsers.add_parser('versao', help=msg_help)

    # tremo_loader
    tremo = TremoLoader()

    args = parser.parse_args()

    # Seta a variável global verbose
    if args.verbose:
        verbose = True

    # Seta a variável global com_timeout
    if args.timeout is not None:
        com_timeout = args.timeout

    # Seta a variável global apaga_eeprom
    if args.eeprom:
        apaga_eeprom = False

    if args.port is None:
        lista_portas_disponiveis = get_lista_portas_com()
        print("Encontrado %d serial ports" % len(lista_portas_disponiveis))
    else:
        lista_portas_disponiveis = [args.port]

    try:
        if args.command == 'jump':
            tremo_jump(args, tremo)
            print('Jump executado com sucesso')
        elif args.command == 'flash':
            tremo_flash(args, tremo)
            print('Gravado com sucesso')
        elif args.command == 'erase':
            tremo_erase(args, tremo)
            print('Apagado com sucesso')
        elif args.command == 'verify':
            tremo_verify(args, tremo)
            print('Verificacao completa! Fash igual ao arquivo.')
        elif args.command == 'escrever_otp':
            tremo_escrever_otp(args, tremo)
            print('Escrita na OTP com sucesso')
        elif args.command == 'ler_otp':
            data = tremo_ler_otp(args, tremo)
            print('OTP data: %s' % binascii.hexlify(data))
        elif args.command == 'escrever_otp0':
            tremo_escrever_otp0(args, tremo)
            print('Escrita na OTP0 com sucesso')
        elif args.command == 'ler_otp0':
            opt0 = tremo_ler_otp0(args, tremo)
            print('OTP0 data: %s %s' % (hex(opt0[0]), hex(opt0[1])))
        elif args.command == 'escrever_otp1':
            tremo_escrever_otp1(args, tremo)
            print('Escrita na OTP1 com sucesso')
        elif args.command == 'ler_otp1':
            opt1 = tremo_ler_otp1(args, tremo)
            print('OTP1 data: %s %s' % (hex(opt1[0]), hex(opt1[1])))
        elif args.command == 'reset':
            tremo_sw_reset(args, tremo)
            print('Reset via software')
        elif args.command == 'serial':
            sn = tremo_serial_asr(args, tremo)
            print('Serial: %s' % binascii.hexlify(sn))
        elif args.command == 'escrever_reg':
            tremo_escrever_reg(args, tremo)
            print('Registrador escrito com sucesso')
        elif args.command == 'ler_reg':
            valor_reg = tremo_ler_reg(args, tremo)
            print('Valor do registrador: 0x%s' % valor_reg[0])
        elif args.command == 'versao_bootloader':
            versao = tremo_versao_bootloader(args, tremo)
            print('Versao do bootloader: %s' % hex(versao[0]))
        elif args.command == 'clear_eeprom':
            tremo_clean_eeprom(args, tremo)
            print('Eeprom emulada apagada com sucesso')
        elif args.command == 'help':
            tremo_print_help(parser)
        elif args.command == 'versao':
            print("Tremo Loader v%s" % VERSAO_GRAVADOR)
        else:
            tremo_print_help(parser)
    except Exception as e:
        print(str(e))
