import contextlib
import io
import tempfile
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from src.runtime import RuntimeConfig
from src.serial_port import SerialPort
from src.utils import (
    arg_int,
    get_crc32,
    get_dispositivo_conectado,
    get_lista_portas_com,
    get_lista_portas_info,
)


class NewStyleSerial:
    def __init__(self):
        self.port = 'COM7'
        self.baudrate = 115200
        self.calls = []
        self.read_data = b'ab'
        self.closed = False

    def read(self, size):
        self.calls.append(('read', size))
        return self.read_data[:size]

    def write(self, data):
        self.calls.append(('write', data))
        return len(data)

    def close(self):
        self.closed = True
        self.calls.append(('close',))

    def setDTR(self, state):
        self.calls.append(('setDTR', state))

    def setRTS(self, state):
        self.calls.append(('setRTS', state))

    def reset_input_buffer(self):
        self.calls.append(('reset_input_buffer',))

    def reset_output_buffer(self):
        self.calls.append(('reset_output_buffer',))


class OldStyleSerial:
    def __init__(self):
        self.port = 'COM8'
        self.baudrate = 9600
        self.dtr = None
        self.rts = None
        self.calls = []

    def read(self, size):
        self.calls.append(('read', size))
        return b''

    def write(self, data):
        self.calls.append(('write', data))
        return len(data)

    def close(self):
        self.calls.append(('close',))

    def flushInput(self):
        self.calls.append(('flushInput',))

    def flushOutput(self):
        self.calls.append(('flushOutput',))


class RuntimeUtilsSerialTests(unittest.TestCase):
    def test_runtime_config_writes_and_closes_log_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / 'logs' / 'run.log'

            config = RuntimeConfig(log_file=log_path)
            config.log('evento de teste')
            config.close_log()
            config.close_log()

            content = log_path.read_text(encoding='utf-8')

        self.assertIn('--- inicio do log ---', content)
        self.assertIn('evento de teste', content)
        self.assertIn('--- fim do log ---', content)
        self.assertIsNone(config._log_handle)

    def test_arg_int_accepts_decimal_and_hex(self):
        self.assertEqual(arg_int('16'), 16)
        self.assertEqual(arg_int('0x10'), 16)

    def test_get_crc32_reads_file_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'fw.bin'
            path.write_bytes(b'abc123')

            crc = get_crc32(path)

        self.assertEqual(crc, zlib.crc32(b'abc123') & 0xFFFFFFFF)

    def test_serial_port_listing_is_sorted(self):
        ports = [
            SimpleNamespace(device='COM9'),
            SimpleNamespace(device='COM1'),
            SimpleNamespace(device='COM3'),
        ]

        with mock.patch('src.utils.list_ports.comports', return_value=ports):
            self.assertEqual(get_lista_portas_com(), ['COM1', 'COM3', 'COM9'])

    def test_serial_port_info_includes_diagnostic_fields(self):
        ports = [
            SimpleNamespace(
                device='COM2',
                name='ttyS2',
                description='CP2102 USB UART',
                hwid='USB VID:PID=10C4:EA60',
                vid=0x10C4,
                pid=0xEA60,
                serial_number='ABC',
                location='1-1',
                manufacturer='Silabs',
                product='CP2102',
                interface='UART',
            ),
            SimpleNamespace(
                device='COM1',
                name='ttyS1',
                description='Other',
                hwid='n/a',
                vid=None,
                pid=None,
                serial_number=None,
                location=None,
                manufacturer=None,
                product=None,
                interface=None,
            ),
        ]

        with mock.patch('src.utils.list_ports.comports', return_value=ports):
            info = get_lista_portas_info()

        self.assertEqual([item['device'] for item in info], ['COM1', 'COM2'])
        self.assertEqual(info[1]['description'], 'CP2102 USB UART')
        self.assertEqual(info[1]['vid'], 0x10C4)
        self.assertEqual(info[1]['pid'], 0xEA60)
        self.assertEqual(info[1]['serial_number'], 'ABC')

    def test_get_dispositivo_conectado_prints_ports_in_reverse_order(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            get_dispositivo_conectado(['COM1', 'COM2'])

        self.assertEqual(stdout.getvalue().splitlines(), ['Serial port COM2', 'Serial port COM1'])

    def test_serial_port_delegates_to_new_pyserial_api(self):
        fake = NewStyleSerial()

        with mock.patch('src.serial_port.serial.Serial', return_value=fake) as serial_ctor:
            port = SerialPort('COM7', 115200, timeout=3)
            self.assertEqual(port.port, 'COM7')
            self.assertEqual(port.baudrate, 115200)
            port.baudrate = 57600
            self.assertEqual(port.baudrate, 57600)
            self.assertEqual(port.read(1), b'a')
            self.assertEqual(port.write(b'xy'), 2)
            port.set_dtr(True)
            port.set_rts(False)
            port.flush_input()
            port.flush_output()
            port.close()

        serial_ctor.assert_called_once_with('COM7', 115200, timeout=3)
        self.assertIn(('setDTR', True), fake.calls)
        self.assertIn(('setRTS', False), fake.calls)
        self.assertIn(('reset_input_buffer',), fake.calls)
        self.assertIn(('reset_output_buffer',), fake.calls)
        self.assertTrue(fake.closed)

    def test_serial_port_falls_back_to_old_pyserial_api(self):
        fake = OldStyleSerial()

        with mock.patch('src.serial_port.serial.Serial', return_value=fake):
            port = SerialPort('COM8', 9600, timeout=1)
            port.set_dtr(False)
            port.set_rts(True)
            port.flush_input()
            port.flush_output()

        self.assertFalse(fake.dtr)
        self.assertTrue(fake.rts)
        self.assertIn(('flushInput',), fake.calls)
        self.assertIn(('flushOutput',), fake.calls)


if __name__ == '__main__':
    unittest.main()
