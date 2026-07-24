import struct
import zlib

from src.constantes import (
    CMD_BAUDRATE,
    CMD_ERASE,
    CMD_FLASH,
    CMD_JUMP,
    CMD_RDREG,
    CMD_REBOOT,
    CMD_SN,
    CMD_SYNC,
    CMD_VERIFY,
    CMD_VERSION,
    CMD_WRREG,
)


class FakeBootloaderSerial:
    def __init__(self, registradores=None, comandos_com_falha=None):
        self.port = 'COM_FAKE'
        self.baudrate = 9600
        self.registradores = dict(registradores or {})
        self.comandos_com_falha = set(comandos_com_falha or [])
        self.resposta = b''
        self.fechada = False
        self.escritas = []
        self.estados_dtr = []
        self.estados_rts = []

    def read(self, tamanho):
        if not self.resposta:
            return b''
        trecho = self.resposta[:tamanho]
        self.resposta = self.resposta[tamanho:]
        return trecho

    def write(self, dados):
        self.escritas.append(dados)
        _inicio, comando, tamanho_carga = struct.unpack('<BBH', dados[:4])
        carga = dados[4:4 + tamanho_carga]
        estado = 1 if comando in self.comandos_com_falha else 0
        carga_resposta = b''

        if estado == 0:
            if comando == CMD_SN:
                carga_resposta = b'1234567890abcdef'
            elif comando == CMD_VERSION:
                carga_resposta = struct.pack('<I', 0x01020304)
            elif comando == CMD_RDREG:
                endereco = struct.unpack('<I', carga)[0]
                carga_resposta = struct.pack('<I', self.registradores.get(endereco, 0))
            elif comando == CMD_WRREG:
                endereco, valor = struct.unpack('<II', carga)
                self.registradores[endereco] = valor
            elif comando in (CMD_SYNC, CMD_BAUDRATE, CMD_ERASE, CMD_FLASH, CMD_VERIFY, CMD_JUMP, CMD_REBOOT):
                carga_resposta = b''

        self.resposta = montar_pacote_resposta(estado=estado, dados=carga_resposta)
        return len(dados)

    def close(self):
        self.fechada = True

    def set_dtr(self, estado):
        self.estados_dtr.append(estado)

    def set_rts(self, estado):
        self.estados_rts.append(estado)

    def flush_input(self):
        pass

    def flush_output(self):
        pass


def montar_pacote_resposta(estado=0, dados=b''):
    cabecalho = struct.pack('<BBH', 0xFE, estado, len(dados))
    crc = zlib.crc32(cabecalho + dados) & 0xFFFFFFFF
    return cabecalho + dados + struct.pack('<IB', crc, 0xEF)
