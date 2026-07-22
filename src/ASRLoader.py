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


class ASRLoader(object):
    def __init__(self, config):
        self.ser = None
        self.config = config
        self._trace_serial = None

    def _trace(self, event, **campos):
        if hasattr(self.config, 'trace'):
            self.config.trace(event, **campos)

    def _trace_serial_result(self, status=None, rx_len=0, rx_hex=None, error=None):
        contexto = self._trace_serial or {}
        inicio = contexto.get('start')
        campos = {
            'cmd': contexto.get('cmd'),
            'tx_len': contexto.get('tx_len'),
            'rx_status': status,
            'rx_len': rx_len,
        }
        if isinstance(inicio, (int, float)):
            campos['duration_ms'] = round((time.perf_counter() - inicio) * 1000, 3)
        if rx_hex is not None:
            campos['rx_hex'] = rx_hex
        if error is not None:
            campos['error'] = error
        self._trace('serial_result', **campos)

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

    def set_dtr(self, estado):
        self.ser.set_dtr(estado)
        self.config.log('DTR=%d' % (1 if estado else 0))

    def set_rts(self, estado):
        self.ser.set_rts(estado)
        self.config.log('RTS=%d' % (1 if estado else 0))

    def hw_reset(self, mode=0):
        self.config.log('hw_reset mode=%d reset_delay=%.3f release_delay=%.3f' % (
            mode,
            self.config.boot_reset_delay,
            self.config.boot_release_delay,
        ))
        if mode:
            self.set_dtr(True)
            self.set_rts(True)
            time.sleep(self.config.boot_reset_delay)
            self.set_rts(False)
            time.sleep(self.config.boot_release_delay)
            self.set_dtr(False)
        else:
            self.set_rts(True)
            time.sleep(self.config.boot_reset_delay)
            self.set_rts(False)

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
        self.config.log('set_baudrate solicitando baud=%d' % baud)
        self.enviar_cmd(CMD_BAUDRATE, struct.pack('<I', baud))
        ret, _ = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel alterar o baud")

        try:
            if self.config.verbose:
                print("baud", baud)
            self.ser.baudrate = baud
            self.config.log('set_baudrate aplicado baud=%d' % baud)
        except IOError:
            raise CmdExcessao("ERROR: nao foi possivel alterar o baud")

    def set_port(self, port, baud=BAUD_DEFAULT):
        self.ser = SerialPort(port, baud, timeout=self.config.com_timeout)
        self.config.log('porta aberta port=%s baud=%d timeout=%s' % (self.ser.port, baud, self.config.com_timeout))

    def versao_bootloader(self):
        self.enviar_cmd(CMD_VERSION)
        ret, rsp = self.aguardar_resposta()
        if ret != 0:
            raise CmdExcessao("ERROR: nao foi possivel ler a versao do bootloader")
        return struct.unpack('<I', rsp)

    def conectar(self, retentativas=3):
        print('Conectando em %s...' % self.ser.port)
        self.config.log('conectar port=%s retentativas=%d auto_boot=%s' % (
            self.ser.port,
            retentativas,
            self.config.auto_boot,
        ))
        sys.stdout.flush()
        last_error = None

        for tentativa in range(1, retentativas + 1):
            try:
                self.config.log('tentativa_conexao=%d' % tentativa)
                if self.config.auto_boot:
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
                self.config.log('tentativa_conexao=%d erro=%s' % (tentativa, excessao))

        if last_error is not None:
            self.ser.close()
            print('Falha na conexao')
            self.config.log('falha_conexao erro=%s' % last_error)
            raise CmdExcessao('Erro de conexao: %s' % last_error)
        print('Conectado. ', end='')
        self.config.log('conectado port=%s' % self.ser.port)
        if self.config.verbose:
            print("\n")

    def enviar_cmd(self, cmd, buf=b""):
        pkt = struct.pack(b'<BBH', 0xFE, cmd, len(buf)) + buf
        checksum = zlib.crc32(pkt) & 0xFFFFFFFF
        pkt += struct.pack(b'<IB', checksum, 0xEF)
        tx_hex = binascii.hexlify(pkt).decode('ascii')
        self._trace_serial = {
            'cmd': cmd,
            'tx_len': len(pkt),
            'start': time.perf_counter(),
        }

        if self.config.verbose:
            print('Tx[%d]:' % len(pkt), binascii.hexlify(pkt))
        self.config.log('Tx[%d]: %s' % (len(pkt), tx_hex))
        self._trace('serial_tx', cmd=cmd, tx_len=len(pkt), tx_hex=tx_hex)

        self.ser.flush_input()
        self.ser.write(pkt)

    def aguardar_resposta(self):
        header = self.ser.read(4)
        if header == b'':
            self.config.log('Rx timeout header')
            self._trace_serial_result(error='timeout_header')
            raise CmdExcessao("ERROR: timeout leitura do header response")
        start, status, rsp_data_len = struct.unpack('<BBH', header)
        if start != 0xFE:
            self._trace_serial_result(status=status, rx_len=len(header), rx_hex=binascii.hexlify(header).decode('ascii'),
                                      error='bad_start_marker')
            raise CmdExcessao("ERROR: pacote de resposta errado")
        if rsp_data_len > 512:
            self._trace_serial_result(status=status, rx_len=len(header), rx_hex=binascii.hexlify(header).decode('ascii'),
                                      error='oversized_payload')
            raise CmdExcessao("ERROR: tamanho do pacote de resposta errado")

        remain_data = self.ser.read(rsp_data_len + 5)
        if remain_data == b'':
            self.config.log('Rx timeout dados')
            self._trace_serial_result(status=status, rx_len=len(header), rx_hex=binascii.hexlify(header).decode('ascii'),
                                      error='timeout_data')
            raise CmdExcessao("ERROR: timeout leitura de dados")

        pkt = header + remain_data
        rx_hex = binascii.hexlify(pkt).decode('ascii')

        if self.config.verbose:
            print('Rx[%d]:' % len(pkt), binascii.hexlify(pkt))
        self.config.log('Rx[%d]: %s' % (len(pkt), rx_hex))

        crc, end = struct.unpack('<IB', pkt[4 + rsp_data_len:])

        if end != 0xEF:
            self._trace_serial_result(status=status, rx_len=len(pkt), rx_hex=rx_hex, error='bad_end_marker')
            raise CmdExcessao("ERROR: pacote de resposta errado")

        checksum = zlib.crc32(pkt[:4 + rsp_data_len]) & 0xFFFFFFFF
        if crc != checksum:
            self._trace_serial_result(status=status, rx_len=len(pkt), rx_hex=rx_hex, error='bad_crc')
            raise CmdExcessao("ERROR: CRC errado")

        self._trace_serial_result(status=status, rx_len=len(pkt), rx_hex=rx_hex)
        return status, pkt[4:4 + rsp_data_len]
