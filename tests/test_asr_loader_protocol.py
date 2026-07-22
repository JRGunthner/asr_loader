import contextlib
import io
import struct
import unittest
from unittest import mock
import zlib

from src.ASRLoader import ASRLoader
from src.constantes import (
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
from src.exceptions import CmdExcessao


class DummyConfig:
    def __init__(self):
        self.verbose = False
        self.com_timeout = 2
        self.auto_boot = True
        self.boot_reset_delay = 0.1
        self.boot_release_delay = 0.2
        self.logs = []

    def log(self, mensagem):
        self.logs.append(mensagem)


class FakeSerial:
    def __init__(self, read_chunks=None):
        self.port = 'COM_TEST'
        self.baudrate = 9600
        self.read_chunks = list(read_chunks or [])
        self.writes = []
        self.dtr_states = []
        self.rts_states = []
        self.flush_input_count = 0
        self.flush_output_count = 0
        self.closed = False

    def read(self, size):
        if not self.read_chunks:
            return b''
        return self.read_chunks.pop(0)

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def close(self):
        self.closed = True

    def set_dtr(self, state):
        self.dtr_states.append(state)

    def set_rts(self, state):
        self.rts_states.append(state)

    def flush_input(self):
        self.flush_input_count += 1

    def flush_output(self):
        self.flush_output_count += 1


def response_packet(status=0, data=b''):
    header = struct.pack('<BBH', 0xFE, status, len(data))
    crc = zlib.crc32(header + data) & 0xFFFFFFFF
    return header + data + struct.pack('<IB', crc, 0xEF)


class ASRLoaderProtocolTests(unittest.TestCase):
    def make_loader(self, fake_serial=None):
        config = DummyConfig()
        loader = ASRLoader(config)
        loader.ser = fake_serial or FakeSerial()
        return loader, config

    def written_command(self, fake_serial, index=0):
        packet = fake_serial.writes[index]
        start, command, payload_len = struct.unpack('<BBH', packet[:4])
        self.assertEqual(start, 0xFE)
        return command, packet[4:4 + payload_len]

    def test_enviar_cmd_builds_packet_with_crc_and_end_marker(self):
        fake = FakeSerial()
        loader, config = self.make_loader(fake)

        loader.enviar_cmd(CMD_SYNC, b'ab')

        self.assertEqual(fake.flush_input_count, 1)
        self.assertEqual(len(fake.writes), 1)
        packet = fake.writes[0]
        self.assertEqual(packet[:4], struct.pack('<BBH', 0xFE, CMD_SYNC, 2))
        self.assertEqual(packet[4:6], b'ab')
        self.assertEqual(packet[-1], 0xEF)
        expected_crc = zlib.crc32(packet[:-5]) & 0xFFFFFFFF
        actual_crc = struct.unpack('<I', packet[-5:-1])[0]
        self.assertEqual(actual_crc, expected_crc)
        self.assertTrue(any('Tx' in item for item in config.logs))

    def test_aguardar_resposta_returns_status_and_payload(self):
        packet = response_packet(status=0, data=b'\x01\x02\x03')
        fake = FakeSerial([packet[:4], packet[4:]])
        loader, config = self.make_loader(fake)

        status, payload = loader.aguardar_resposta()

        self.assertEqual(status, 0)
        self.assertEqual(payload, b'\x01\x02\x03')
        self.assertTrue(any('Rx' in item for item in config.logs))

    def test_aguardar_resposta_rejects_bad_start_marker(self):
        header = struct.pack('<BBH', 0x00, 0, 0)
        fake = FakeSerial([header])
        loader, _config = self.make_loader(fake)

        with self.assertRaisesRegex(CmdExcessao, 'pacote de resposta errado'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_rejects_bad_crc(self):
        packet = bytearray(response_packet(status=0, data=b'x'))
        packet[-5] ^= 0xFF
        fake = FakeSerial([bytes(packet[:4]), bytes(packet[4:])])
        loader, _config = self.make_loader(fake)

        with self.assertRaisesRegex(CmdExcessao, 'CRC errado'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_rejects_bad_end_marker(self):
        packet = bytearray(response_packet(status=0, data=b'x'))
        packet[-1] = 0
        fake = FakeSerial([bytes(packet[:4]), bytes(packet[4:])])
        loader, _config = self.make_loader(fake)

        with self.assertRaisesRegex(CmdExcessao, 'pacote de resposta errado'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_rejects_oversized_payload(self):
        fake = FakeSerial([struct.pack('<BBH', 0xFE, 0, 513)])
        loader, _config = self.make_loader(fake)

        with self.assertRaisesRegex(CmdExcessao, 'tamanho do pacote'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_times_out_on_empty_header(self):
        fake = FakeSerial([b''])
        loader, config = self.make_loader(fake)

        with self.assertRaisesRegex(CmdExcessao, 'timeout leitura do header'):
            loader.aguardar_resposta()
        self.assertIn('Rx timeout header', config.logs)

    def test_aguardar_resposta_times_out_on_empty_payload(self):
        fake = FakeSerial([struct.pack('<BBH', 0xFE, 0, 1), b''])
        loader, config = self.make_loader(fake)

        with self.assertRaisesRegex(CmdExcessao, 'timeout leitura de dados'):
            loader.aguardar_resposta()
        self.assertIn('Rx timeout dados', config.logs)

    def test_write_commands_send_expected_payloads(self):
        cases = [
            (
                'jump',
                lambda loader: loader.jump(0x08000123),
                CMD_JUMP,
                struct.pack('<I', 0x08000123),
            ),
            (
                'flash',
                lambda loader: loader.flash(0x08000000, b'abcd'),
                CMD_FLASH,
                struct.pack('<II', 0x08000000, 4) + b'abcd',
            ),
            (
                'erase',
                lambda loader: loader.erase(0x08000000, 4096),
                CMD_ERASE,
                struct.pack('<II', 0x08000000, 4096),
            ),
            (
                'verify',
                lambda loader: loader.verify(0x08000000, 128, 0x12345678),
                CMD_VERIFY,
                struct.pack('<III', 0x08000000, 128, 0x12345678),
            ),
            (
                'escrever_otp',
                lambda loader: loader.escrever_otp(0x1FFF7000, b'\xAA\x55'),
                CMD_WROTP,
                struct.pack('<II', 0x1FFF7000, 2) + b'\xAA\x55',
            ),
            (
                'escrever_opt0',
                lambda loader: loader.escrever_opt0(0x11223344, 0x55667788),
                CMD_WROPT0,
                struct.pack('<II', 0x11223344, 0x55667788),
            ),
            (
                'escrever_opt1',
                lambda loader: loader.escrever_opt1(0x99AABBCC, 0xDDEEFF00),
                CMD_WROPT1,
                struct.pack('<II', 0x99AABBCC, 0xDDEEFF00),
            ),
            (
                'sw_reset',
                lambda loader: loader.sw_reset(1),
                CMD_REBOOT,
                struct.pack('B', 1),
            ),
            (
                'escrever_reg',
                lambda loader: loader.escrever_reg(0x40021000, 0x1234),
                CMD_WRREG,
                struct.pack('<II', 0x40021000, 0x1234),
            ),
        ]

        for name, action, expected_command, expected_payload in cases:
            with self.subTest(name=name):
                packet = response_packet(status=0)
                fake = FakeSerial([packet[:4], packet[4:]])
                loader, _config = self.make_loader(fake)

                action(loader)

                command, payload = self.written_command(fake)
                self.assertEqual(command, expected_command)
                self.assertEqual(payload, expected_payload)

    def test_read_commands_return_decoded_payloads(self):
        cases = [
            (
                'ler_otp',
                lambda loader: loader.ler_otp(0x1FFF7000, 4),
                CMD_RDOTP,
                struct.pack('<II', 0x1FFF7000, 4),
                b'abcd',
                b'abcd',
            ),
            (
                'ler_opt0',
                lambda loader: loader.ler_opt0(),
                CMD_RDOPT0,
                b'',
                struct.pack('<II', 0x11223344, 0x55667788),
                (0x11223344, 0x55667788),
            ),
            (
                'ler_opt1',
                lambda loader: loader.ler_opt1(),
                CMD_RDOPT1,
                b'',
                struct.pack('<II', 0x99AABBCC, 0xDDEEFF00),
                (0x99AABBCC, 0xDDEEFF00),
            ),
            (
                'ler_reg',
                lambda loader: loader.ler_reg(0x40021000),
                CMD_RDREG,
                struct.pack('<I', 0x40021000),
                struct.pack('<I', 0x12345678),
                (0x12345678,),
            ),
            (
                'versao_bootloader',
                lambda loader: loader.versao_bootloader(),
                CMD_VERSION,
                b'',
                struct.pack('<I', 0x01020304),
                (0x01020304,),
            ),
        ]

        for name, action, expected_command, expected_payload, response_payload, expected_result in cases:
            with self.subTest(name=name):
                packet = response_packet(status=0, data=response_payload)
                fake = FakeSerial([packet[:4], packet[4:]])
                loader, _config = self.make_loader(fake)

                result = action(loader)

                command, payload = self.written_command(fake)
                self.assertEqual(command, expected_command)
                self.assertEqual(payload, expected_payload)
                self.assertEqual(result, expected_result)

    def test_command_methods_raise_on_nonzero_status(self):
        cases = [
            ('jump', lambda loader: loader.jump(0x08000123)),
            ('flash', lambda loader: loader.flash(0x08000000, b'abcd')),
            ('erase', lambda loader: loader.erase(0x08000000, 4096)),
            ('verify', lambda loader: loader.verify(0x08000000, 128, 0x12345678)),
            ('escrever_otp', lambda loader: loader.escrever_otp(0x1FFF7000, b'\xAA')),
            ('ler_otp', lambda loader: loader.ler_otp(0x1FFF7000, 4)),
            ('escrever_opt0', lambda loader: loader.escrever_opt0(1, 2)),
            ('ler_opt0', lambda loader: loader.ler_opt0()),
            ('escrever_opt1', lambda loader: loader.escrever_opt1(1, 2)),
            ('ler_opt1', lambda loader: loader.ler_opt1()),
            ('sw_reset', lambda loader: loader.sw_reset()),
            ('serial_asr', lambda loader: loader.serial_asr()),
            ('escrever_reg', lambda loader: loader.escrever_reg(0x40021000, 1)),
            ('ler_reg', lambda loader: loader.ler_reg(0x40021000)),
            ('versao_bootloader', lambda loader: loader.versao_bootloader()),
        ]

        for name, action in cases:
            with self.subTest(name=name):
                packet = response_packet(status=1)
                fake = FakeSerial([packet[:4], packet[4:]])
                loader, _config = self.make_loader(fake)

                with self.assertRaises(CmdExcessao):
                    action(loader)

    def test_serial_asr_returns_payload_when_status_ok(self):
        packet = response_packet(status=0, data=b'1234567890abcdef')
        fake = FakeSerial([packet[:4], packet[4:]])
        loader, _config = self.make_loader(fake)

        serial = loader.serial_asr()

        self.assertEqual(serial, b'1234567890abcdef')
        command, payload = self.written_command(fake)
        self.assertEqual(command, CMD_SN)
        self.assertEqual(payload, b'')

    def test_set_baudrate_sends_command_and_updates_serial_baudrate(self):
        packet = response_packet(status=0)
        fake = FakeSerial([packet[:4], packet[4:]])
        loader, config = self.make_loader(fake)

        loader.set_baudrate(115200)

        self.assertEqual(fake.baudrate, 115200)
        command, payload = self.written_command(fake)
        self.assertEqual(command, CMD_BAUDRATE)
        self.assertEqual(payload, struct.pack('<I', 115200))
        self.assertTrue(any('set_baudrate aplicado' in item for item in config.logs))

    def test_set_port_uses_serial_adapter_and_configured_timeout(self):
        config = DummyConfig()
        loader = ASRLoader(config)
        fake = FakeSerial()

        with mock.patch('src.ASRLoader.SerialPort', return_value=fake) as serial_port:
            loader.set_port('COM9', 57600)

        serial_port.assert_called_once_with('COM9', 57600, timeout=config.com_timeout)
        self.assertIs(loader.ser, fake)
        self.assertTrue(any('porta aberta' in item for item in config.logs))

    def test_hw_reset_boot_sequence_sets_dtr_and_rts_in_order(self):
        fake = FakeSerial()
        loader, _config = self.make_loader(fake)

        with mock.patch('src.ASRLoader.time.sleep') as sleep_mock:
            loader.hw_reset(1)

        self.assertEqual(fake.dtr_states, [True, False])
        self.assertEqual(fake.rts_states, [True, False])
        sleep_mock.assert_has_calls([mock.call(0.1), mock.call(0.2)])

    def test_conectar_without_auto_boot_only_syncs(self):
        packet = response_packet(status=0)
        fake = FakeSerial([packet[:4], packet[4:]])
        loader, config = self.make_loader(fake)
        config.auto_boot = False

        with contextlib.redirect_stdout(io.StringIO()):
            loader.conectar(retentativas=1)

        self.assertEqual(fake.dtr_states, [])
        self.assertEqual(fake.rts_states, [])
        self.assertEqual(fake.flush_output_count, 1)
        self.assertEqual(fake.writes[0][1], CMD_SYNC)

    def test_conectar_retries_and_closes_serial_when_sync_fails(self):
        fake = FakeSerial([b'', b''])
        loader, config = self.make_loader(fake)
        config.auto_boot = False

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(CmdExcessao, 'Erro de conexao'):
                loader.conectar(retentativas=2)

        self.assertTrue(fake.closed)
        self.assertEqual(len(fake.writes), 2)
        self.assertTrue(any('falha_conexao' in item for item in config.logs))


if __name__ == '__main__':
    unittest.main()
