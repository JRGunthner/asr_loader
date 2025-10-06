import argparse

import serial
import os
import sys
import time
import struct
import zlib
import binascii
import serial.tools.list_ports as list_ports

ser_list = []
verbose: bool = False
com_timeout = 2

class TremoLoader(object):
    DEFAULT_PORT = "COM4"
    DEFAULT_BAUD = 921600

    CMD_SYNC     = 1
    CMD_JUMP     = 2
    CMD_FLASH    = 3
    CMD_ERASE    = 4
    CMD_VERIFY   = 5
    CMD_WROTP    = 6
    CMD_RDOTP    = 7
    CMD_WROPT0   = 8
    CMD_RDOPT0   = 9
    CMD_WROPT1   = 10
    CMD_RDOPT1   = 11
    CMD_REBOOT   = 12
    CMD_SN       = 13
    CMD_WRREG    = 14
    CMD_RDREG    = 15
    CMD_BAUDRATE = 16
    CMD_VERSION  = 17
    CMD_PORT     = 18

    def __init__(self):
        self.ser = None

    def wait_response(self):
        header = self.ser.read(4)
        if header == b'':
            raise CmdException("ERROR: timeout leitura do header response")
        (start, status, rsp_data_len) = struct.unpack('<BBH', header)
        if start != 0xFE:
            raise CmdException("ERROR: pacote de resposta errado")
        if rsp_data_len > 512:
            raise CmdException("ERROR: tamanho do pacote de resposta errado")

        remain_data = self.ser.read(rsp_data_len+5)
        if remain_data == b'':
            raise CmdException("ERROR: timeout leitura de dados")

        pkt = header + remain_data

        if verbose:
            print(f'Rx[{len(pkt)}]:', binascii.hexlify(pkt))

        (crc, end) = struct.unpack('<IB', pkt[4+rsp_data_len:])

        if end != 0xEF:
            raise CmdException("ERROR: pacote de resposta errado")

        checksum = zlib.crc32(pkt[:4+rsp_data_len]) & 0xFFFFFFFF
        if crc != checksum:
            raise CmdException("ERROR: CRC errado")

        return status, pkt[4:4+rsp_data_len]

    def requeset(self, cmd, buf=b""):
        pkt = struct.pack(b'<BBH', 0xFE, cmd, len(buf)) + buf
        checksum = zlib.crc32(pkt) & 0xFFFFFFFF
        pkt += struct.pack(b'<IB', checksum, 0xEF)

        if verbose:
            print(f'Tx[{len(pkt)}]:', binascii.hexlify(pkt))

        self.ser.flushInput()
        self.ser.write(pkt)

    def sync(self):
        self.requeset(self.CMD_SYNC)
        self.wait_response()

    def hw_reset(self, mode=0):
        if mode:
            self.ser.setDTR(True)  # gpio2 1
            self.ser.setRTS(True)  # rst 0
            time.sleep(0.1)
            self.ser.setRTS(False)  # rst 1
            time.sleep(0.1)
            self.ser.setDTR(False)  # gpio2 0
        else:
            self.ser.setRTS(True) # rst 0
            time.sleep(0.1)
            self.ser.setRTS(False) # rst 1

    def connect(self, retry=3):
        print('Conectando em %s...' % self.ser.port)
        sys.stdout.flush()
        last_error = None

        for _ in range(retry):
            try:
                self.hw_reset(1)

                last_error = None
                self.ser.flushInput()
                self.ser.flushOutput()
                self.sync()
                break
            except CmdException as e:
                sys.stdout.flush()
                time.sleep(0.05)
                last_error = e

        if last_error is not None:
            self.ser.close()
            print('Falha na conexao')
            raise CmdException('Erro de conexao: %s' % last_error)
        print('Conectado. ', end='')
        if verbose:
            print("\n")

    def erase(self, addr, size):
        self.requeset(self.CMD_ERASE, struct.pack('<II', addr, size))
        ret, _ = self.wait_response()

        if verbose:
            print('Apagando %d bytes em %s...' % (size, hex(addr)))

        if ret != 0:
            raise CmdException("ERROR: falha ao apagar a flash")

    def flash(self, addr, image_data):
        self.requeset(self.CMD_FLASH, struct.pack('<II', addr, len(image_data)) + image_data)
        ret, _ = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: falha ao gravar a flash")

    def verify(self, addr, size, checksum):
        self.requeset(self.CMD_VERIFY, struct.pack('<III', addr, size, checksum))
        ret, _ = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: flash diferente do arquivo")

    def jump(self, addr):
        self.requeset(self.CMD_JUMP, struct.pack('<I', addr))
        ret, _ = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: falha no jump")

    def escrever_otp(self, addr, buffer):
        self.requeset(self.CMD_WROTP, struct.pack('<II', addr, len(buffer)) + buffer)
        ret, rsp = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: escrever_otp")

    def ler_otp(self, addr, size):
        self.requeset(self.CMD_RDOTP, struct.pack('<II', addr, size))
        ret, rsp = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: ler_otp")
        return rsp

    def reboot(self, mode=0):
        self.requeset(self.CMD_REBOOT, struct.pack('B', mode))
        ret, _ = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: nao foi possivel reiniciar")

    def serial_asr(self):
        self.requeset(self.CMD_SN)
        ret, rsp = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: falha na leitura do serial")
        return rsp

    def escrever_reg(self, addr, value):
        self.requeset(self.CMD_WRREG, struct.pack('<II', addr, value))
        ret, _ = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: escrever_reg")

    def ler_reg(self, addr):
        self.requeset(self.CMD_RDREG, struct.pack('<I', addr))
        ret, rsp = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: ler_reg")
        return struct.unpack('<I', rsp)

    def set_baudrate(self, baud):
        self.requeset(self.CMD_BAUDRATE, struct.pack('<I', baud))
        ret, _ = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: nao foi possivel alterar o baud")

        try:
            print("baud", baud)
            self.ser.baudrate = baud
        except IOError:
            raise CmdException("ERROR: nao foi possivel alterar o baud")

    def set_port(self, port, baud=DEFAULT_BAUD):
        self.ser = serial.Serial(port, baud, timeout=com_timeout)

    def versao_bootloader(self):
        self.requeset(self.CMD_VERSION)
        ret, rsp = self.wait_response()
        if ret != 0:
            raise CmdException("ERROR: nao foi possivel ler a versao do bootloader")
        return struct.unpack('<I', rsp)


class CmdException(Exception):
    pass


def arg_int(x):
    return int(x, 0)


def get_crc32(filename):
    with open(filename, 'rb') as f:
        return zlib.crc32(f.read()) & 0xFFFFFFFF


def tremo_erase(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    tremo.erase(param.address, param.size)
    tremo.reboot(0)


def tremo_flash(param):
    # check args
    download_files = []
    for i in range(0, len(param.addr_file), 2):
        try:
            address = int(param.addr_file[i], 0)
        except Exception:
            raise Exception('ERROR: o endereco "%s" deve ser um numero' % param.addr_file[i])

        if not os.access(param.addr_file[i + 1], os.R_OK):
            raise Exception('ERROR: falha na leitura do arquivo: %s' % param.addr_file[i + 1])
        download_files.append((address, param.addr_file[i + 1]))

    # flash
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)

    # limpa a eeprom emulada
    tremo.erase(0x0801f000, 256)

    for address, filename in download_files:
        image_size = os.path.getsize(filename)
        image_checksum = get_crc32(filename)
        tremo.erase(address, image_size)

        flash_addr = address

        if verbose:
            print('Gravando', f' {filename} no endereco {hex(address)}...')
        else:
            print('Gravando', end='', flush=True)

        with open(filename, 'rb') as f:
            l = 0
            while True:
                line_data = f.read(512)
                if line_data == b'':
                    break

                tremo.flash(flash_addr, line_data)
                flash_addr += len(line_data)
                l += len(line_data)
                # print("send: ", l)
                if not verbose:
                    print('.', end='', flush=True)
        tremo.verify(address, image_size, image_checksum)

    if not verbose:
        print('.')

    tremo.reboot(0)


def tremo_escrever_otp(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    tremo.escrever_otp(param.address, binascii.unhexlify(param.data))


def tremo_ler_otp(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    return tremo.ler_otp(param.address, param.size)

def tremo_serial_asr(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    return tremo.serial_asr()


def tremo_reboot(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    return tremo.reboot(0)


def tremo_verify(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)

    # Calcula o CRC32 do arquivo
    image_checksum = get_crc32(param.filename)
    image_size = os.path.getsize(param.filename)

    print(f'Verificando {param.filename} no endereco {hex(param.address)}...')
    tremo.verify(param.address, image_size, image_checksum)


def tremo_versao_bootloader(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    return tremo.versao_bootloader()


def tremo_ler_reg(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    return tremo.ler_reg(param.address)


def tremo_escrever_reg(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    tremo.escrever_reg(param.address, param.value)


def tremo_jump(param):
    tremo = TremoLoader()

    for each_port in reversed(ser_list):
        print("Serial port %s" % each_port)
        try:
            tremo.set_port(each_port)
            tremo.connect()
            break
        except:
            print("Nao foi possivel conectar em %s" % each_port)

    tremo.set_baudrate(param.baud)
    tremo.jump(param.address)


def get_port_list():
    return sorted(ports.device for ports in list_ports.comports())


def get_default_connected_device(serial_list):
    for each_port in reversed(serial_list):
        print("Serial port %s" % each_port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--port', '-p',
        help='serial port'
    )

    parser.add_argument(
        '--baud', '-b',
        help='baud rate',
        type=int,
        default=921600)

    parser.add_argument(
        '--verbose', '-v',
        help='modo verbose para debug',
        action='store_true'
    )

    parser.add_argument(
        '--timeout', '-t',
        help='timeout da serial em segundos, default 2s',
        type=int,
        default=2
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='run tremo_loader.py {command} -h')

    # erase
    parser_erase = subparsers.add_parser('erase', help='apagar determinada area da flash')
    parser_erase.add_argument('address', help='endereco da flash a ser apagada', type=arg_int)
    parser_erase.add_argument('size', help='quantidade de bytes a serem apagados', type=arg_int)

    # flash
    parser_flash = subparsers.add_parser('flash', help='apagar e gravar a flash')
    parser_flash.add_argument('addr_file', metavar='<address> <filename>',
                               help='endereco e nome do arquivo, Ex.: 0x08000000 app.bin', nargs='+')

    # escrever_otp
    parser_escrever_otp = subparsers.add_parser('escrever_otp', help='escrever em uma area da opt da flash')
    parser_escrever_otp.add_argument('address', help='endereco flash otp', type=arg_int)
    parser_escrever_otp.add_argument('data', help='dado a ser escrito na flash')

    # ler_otp
    parser_ler_otp = subparsers.add_parser('ler_otp', help='ler a area da otp da flash')
    parser_ler_otp.add_argument('address', help='endereco flash otp', type=arg_int)
    parser_ler_otp.add_argument('size', help='endereco flash otp', type=arg_int)

    # serial
    parser_serial = subparsers.add_parser('serial', help='ler o serial do ASR')

    # reset
    parser_reset = subparsers.add_parser('reset', help='resetar o ASR')

    # verify
    parser_verify = subparsers.add_parser('verify', help='verificar o conteudo da flash')
    parser_verify.add_argument('address', help='endereco da flash a ser verificado', type=arg_int)
    parser_verify.add_argument('filename', help='arquivo para comparar com a flash')

    # versao_bootloader
    parser_versao_bootloader = subparsers.add_parser('versao_bootloader', help='ler a versao do bootloader')

    # ler_reg
    parser_ler_reg = subparsers.add_parser('ler_reg', help='ler o conteudo de um registrador')
    parser_ler_reg.add_argument('address', help='endereco do registrador a ser lido', type=arg_int)

    # escrever_reg
    parser_escrever_reg = subparsers.add_parser('escrever_reg', help='escrever em um registrador')
    parser_escrever_reg.add_argument('address', help='endereco do registrador a ser escrito', type=arg_int)
    parser_escrever_reg.add_argument('value', help='valor a ser escrito', type=arg_int)

    # jump
    parser_jump = subparsers.add_parser('jump', help='executar um jump para um endereco')
    parser_jump.add_argument('address', help='endereco para onde o jump deve ser feito', type=arg_int)

    args = parser.parse_args()

    # Seta a variável global verbose
    if args.verbose:
        verbose = True

    if args.port is None:
        ser_list = get_port_list()
        print("Encontrado %d serial ports" % len(ser_list))
    else:
        ser_list = [args.port]

    try:
        if args.command == 'erase':
            tremo_erase(args)
            print('Apagado com sucesso')
        elif args.command == 'flash':
            tremo_flash(args)
            print('Gravado com sucesso')
        elif args.command == 'escrever_otp':
            tremo_escrever_otp(args)
            print('Escrita na OTP com sucesso')
        elif args.command == 'ler_otp':
            data = tremo_ler_otp(args)
            print('OTP data: %s' % binascii.hexlify(data))
        elif args.command == 'serial':
            sn = tremo_serial_asr(args)
            print('Serial: %s' % binascii.hexlify(sn))
        elif args.command == 'reset':
            tremo_reboot(args)
            print('Reset')
        elif args.command == 'verify':
            tremo_verify(args)
            print('Verificacao completa! Fash igual ao arquivo.')
        elif args.command == 'versao_bootloader':
            versao = tremo_versao_bootloader(args)
            print('Versao do bootloader: %s' % hex(versao[0]))
        elif args.command == 'ler_reg':
            valor_reg = tremo_ler_reg(args)
            print('Valor do registrador: 0x%s' % valor_reg[0].hex())
        elif args.command == 'escrever_reg':
            print('Registrador escrito com sucesso')
        elif args.command == 'jump':
            print('Jump executado com sucesso')
    except Exception as e:
        print(str(e))
