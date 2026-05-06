import binascii
import os

from .constantes import EEPROM_ENDERECO, EEPROM_SIZE
from .utils import get_crc32


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


def tremo_erase(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.erase(param.address, param.size)
    processador.sw_reset(0)


def apagar_eeprom(processador):
    processador.erase(EEPROM_ENDERECO, EEPROM_SIZE)


def tremo_clean_eeprom(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    apagar_eeprom(processador)
    processador.sw_reset(0)


def tremo_flash(param, processador, config):
    if len(param.addr_file) % 2 != 0:
        raise Exception('ERROR: informe pares <address> <filename>')

    arquivos = []
    for i in range(0, len(param.addr_file), 2):
        try:
            endereco = int(param.addr_file[i], 0)
        except Exception:
            raise Exception('ERROR: o endereco "%s" deve ser um numero' % param.addr_file[i])

        arquivo = param.addr_file[i + 1]
        if not os.access(arquivo, os.R_OK):
            raise Exception('ERROR: falha na leitura do arquivo: %s' % arquivo)
        arquivos.append((endereco, arquivo))

    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return

    if config.apaga_eeprom:
        apagar_eeprom(processador)

    for endereco, pacote in arquivos:
        pacote_len = os.path.getsize(pacote)
        crc_pacote = get_crc32(pacote)
        processador.erase(endereco, pacote_len)

        endereco_na_flash = endereco

        if config.verbose:
            print('Gravando', ' %s no endereco %s...' % (pacote, hex(endereco)))
        else:
            print('Gravando', end='', flush=True)

        with open(pacote, 'rb') as arquivo:
            while True:
                line_data = arquivo.read(512)
                if line_data == b'':
                    break

                processador.flash(endereco_na_flash, line_data)
                endereco_na_flash += len(line_data)
                if not config.verbose:
                    print('.', end='', flush=True)

        processador.verify(endereco, pacote_len, crc_pacote)

    if not config.verbose:
        print('.')

    processador.sw_reset(0)


def tremo_escrever_otp(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_otp(param.address, binascii.unhexlify(param.data))


def tremo_ler_otp(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.ler_otp(param.address, param.size)


def tremo_escrever_opt0(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_opt0(param.opt0_l, param.opt0_h)


def tremo_ler_opt0(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt0()


def tremo_escrever_opt1(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_opt1(param.opt1_l, param.opt1_h)


def tremo_ler_opt1(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt1()


def tremo_serial_asr(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.serial_asr()


def tremo_sw_reset(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.sw_reset(0)


def tremo_verify(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return

    image_checksum = get_crc32(param.filename)
    image_size = os.path.getsize(param.filename)

    print('Verificando %s no endereco %s...' % (param.filename, hex(param.address)))
    processador.verify(param.address, image_size, image_checksum)


def tremo_versao_bootloader(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return (0,)
    return processador.versao_bootloader()


def tremo_ler_reg(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return (0,)
    return processador.ler_reg(param.address)


def tremo_escrever_reg(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_reg(param.address, param.value)


def tremo_jump(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.jump(param.address)

