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
    def __init__(self, registers=None, fail_commands=None):
        self.port = 'COM_FAKE'
        self.baudrate = 9600
        self.registers = dict(registers or {})
        self.fail_commands = set(fail_commands or [])
        self.response = b''
        self.closed = False
        self.writes = []
        self.dtr_states = []
        self.rts_states = []

    def read(self, size):
        if not self.response:
            return b''
        chunk = self.response[:size]
        self.response = self.response[size:]
        return chunk

    def write(self, data):
        self.writes.append(data)
        _start, command, payload_len = struct.unpack('<BBH', data[:4])
        payload = data[4:4 + payload_len]
        status = 1 if command in self.fail_commands else 0
        response_payload = b''

        if status == 0:
            if command == CMD_SN:
                response_payload = b'1234567890abcdef'
            elif command == CMD_VERSION:
                response_payload = struct.pack('<I', 0x01020304)
            elif command == CMD_RDREG:
                address = struct.unpack('<I', payload)[0]
                response_payload = struct.pack('<I', self.registers.get(address, 0))
            elif command == CMD_WRREG:
                address, value = struct.unpack('<II', payload)
                self.registers[address] = value
            elif command in (CMD_SYNC, CMD_BAUDRATE, CMD_ERASE, CMD_FLASH, CMD_VERIFY, CMD_JUMP, CMD_REBOOT):
                response_payload = b''

        self.response = response_packet(status=status, data=response_payload)
        return len(data)

    def close(self):
        self.closed = True

    def set_dtr(self, state):
        self.dtr_states.append(state)

    def set_rts(self, state):
        self.rts_states.append(state)

    def flush_input(self):
        pass

    def flush_output(self):
        pass


def response_packet(status=0, data=b''):
    header = struct.pack('<BBH', 0xFE, status, len(data))
    crc = zlib.crc32(header + data) & 0xFFFFFFFF
    return header + data + struct.pack('<IB', crc, 0xEF)
