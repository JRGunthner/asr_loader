import binascii
import struct
import sys
import time
import zlib

from .constantes import (
    BAUD_DEFAULT,
    CMD_BAUDRATE,
    CMD_ERASE,
    CMD_FLASH,
    CMD_JUMP,
    CMD_RDOTP,
    CMD_RDOPT0,
    CMD_RDOPT1,
    CMD_RDREG,
    CMD_REBOOT,
    CMD_SN,
    CMD_SYNC,
    CMD_VERIFY,
    CMD_VERSION,
    CMD_WROPT0,
    CMD_WROPT1,
    CMD_WROTP,
    CMD_WRREG,
)
from .exceptions import CmdExcessao
from .serial_port import SerialPort


class TremoLoader(object):
    def __init__(self, config):
        self.ser = None
        self.config = config

    def sync(self):
        self.enviar_cmd(CMD_SYNC)
        self.aguardar_resposta()

    def jump(self, addr):
        self.enviar_cmd(CMD_JUMP, struct.pack('<I', addr))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: falha no jump")

    def flash(self, addr, arquivo_bin):
        arq_len = len(arquivo_bin)
        self.enviar_cmd(CMD_FLASH, struct.pack('<II', addr, arq_len) + arquivo_bin)
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: falha ao gravar a flash")

    def erase(self, addr, size):
        self.enviar_cmd(CMD_ERASE, struct.pack('<II', addr, size))
        ret, _ = self.aguardar_resposta()

        if self.config.verbose:
            print('Apagando %d bytes em %s...' % (size, hex(addr)))

        if ret != 0:
            raise CmdExcessao("ERROR: falha ao apagar a flash")

    def verify(self, addr, size, checksum):
        self.enviar_cmd(CMD_VERIFY, struct.pack('<III', addr, size, checksum))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: flash diferente do arquivo")

    def escrever_otp(self, addr, buffer):
        buf_len = len(buffer)
        self.enviar_cmd(CMD_WROTP, struct.pack('<II', addr, buf_len) + buffer)
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_otp")

    def ler_otp(self, addr, size):
        self.enviar_cmd(CMD_RDOTP, struct.pack('<II', addr, size))
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_otp")
        return rsp

    def escrever_opt0(self, opt0_l, opt0_h):
        self.enviar_cmd(CMD_WROPT0, struct.pack('<II', opt0_l, opt0_h))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_opt0")

    def ler_opt0(self):
        self.enviar_cmd(CMD_RDOPT0)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_opt0")
        return struct.unpack('<II', rsp)

    def escrever_opt1(self, opt1_l, opt1_h):
        self.enviar_cmd(CMD_WROPT1, struct.pack('<II', opt1_l, opt1_h))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_opt1")

    def ler_opt1(self):
        self.enviar_cmd(CMD_RDOPT1)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_opt1")
        return struct.unpack('<II', rsp)

    def sw_reset(self, mode=0):
        self.enviar_cmd(CMD_REBOOT, struct.pack('B', mode))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel reiniciar")

    def hw_reset(self, mode=0):
        if mode:
            self.ser.set_dtr(True)
            self.ser.set_rts(True)
            time.sleep(0.1)
            self.ser.set_rts(False)
            time.sleep(0.1)
            self.ser.set_dtr(False)
        else:
            self.ser.set_rts(True)
            time.sleep(0.1)
            self.ser.set_rts(False)

    def serial_asr(self):
        self.enviar_cmd(CMD_SN)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: falha na leitura do serial")
        return rsp

    def escrever_reg(self, addr, valor):
        self.enviar_cmd(CMD_WRREG, struct.pack('<II', addr, valor))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: escrever_reg")

    def ler_reg(self, addr):
        self.enviar_cmd(CMD_RDREG, struct.pack('<I', addr))
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: ler_reg")
        return struct.unpack('<I', rsp)

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

    def set_port(self, port, baud=BAUD_DEFAULT):
        self.ser = SerialPort(port, baud, timeout=self.config.com_timeout)

    def versao_bootloader(self):
        self.enviar_cmd(CMD_VERSION)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel ler a versao do bootloader")
        return struct.unpack('<I', rsp)

    def conectar(self, retentativas=3):
        print('Conectando em %s...' % self.ser.port)
        sys.stdout.flush()
        last_error = None

        for _ in range(retentativas):
            try:
                self.hw_reset(1)
                last_error = None
                self.ser.flush_input()
                self.ser.flush_output()
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
        if self.config.verbose:
            print("\n")

    def enviar_cmd(self, cmd, buf=b""):
        pkt = struct.pack(b'<BBH', 0xFE, cmd, len(buf)) + buf
        checksum = zlib.crc32(pkt) & 0xFFFFFFFF
        pkt += struct.pack(b'<IB', checksum, 0xEF)

        if self.config.verbose:
            print('Tx[%d]:' % len(pkt), binascii.hexlify(pkt))

        self.ser.flush_input()
        self.ser.write(pkt)

    def aguardar_resposta(self):
        header = self.ser.read(4)
        if header == b'':
            raise CmdExcessao("ERROR: timeout leitura do header response")
        start, status, rsp_data_len = struct.unpack('<BBH', header)
        if start != 0xFE:
            raise CmdExcessao("ERROR: pacote de resposta errado")
        if rsp_data_len > 512:
            raise CmdExcessao("ERROR: tamanho do pacote de resposta errado")

        remain_data = self.ser.read(rsp_data_len + 5)
        if remain_data == b'':
            raise CmdExcessao("ERROR: timeout leitura de dados")

        pkt = header + remain_data

        if self.config.verbose:
            print('Rx[%d]:' % len(pkt), binascii.hexlify(pkt))

        crc, end = struct.unpack('<IB', pkt[4 + rsp_data_len:])

        if end != 0xEF:
            raise CmdExcessao("ERROR: pacote de resposta errado")

        checksum = zlib.crc32(pkt[:4 + rsp_data_len]) & 0xFFFFFFFF
        if crc != checksum:
            raise CmdExcessao("ERROR: CRC errado")

        return status, pkt[4:4 + rsp_data_len]
