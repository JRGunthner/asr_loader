import contextlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.cli import cli_build_parser, main
from src.constantes import ASR_APP_FLASH_START
from src.diagnosticos import analisar_firmware_bytes, montar_preflight_flash, parse_csv_floats, parse_csv_ints

from tests.fake_bootloader import FakeBootloaderSerial


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = main(argv)
    return exit_code, stdout.getvalue(), stderr.getvalue()


class DiagnosticsFeatureTests(unittest.TestCase):
    def test_parser_registers_new_diagnostic_commands(self):
        parser = cli_build_parser()

        self.assertEqual(parser.parse_args(['doctor']).command, 'doctor')
        self.assertEqual(parser.parse_args(['snapshot']).command, 'snapshot')
        self.assertEqual(parser.parse_args(['firmware_inspect', 'app.bin']).command, 'firmware_inspect')
        self.assertEqual(parser.parse_args(['preflight', '0x08000000', 'app.bin']).command, 'preflight')

    def test_csv_parsers_accept_decimal_hex_and_reject_empty_values(self):
        self.assertEqual(parse_csv_floats('0,0.1,0.2'), [0.0, 0.1, 0.2])
        self.assertEqual(parse_csv_ints('115200,0xE1000'), [115200, 921600])
        with self.assertRaises(ValueError):
            parse_csv_floats('')
        with self.assertRaises(ValueError):
            parse_csv_ints('0')

    def test_firmware_analysis_detects_valid_vector_table(self):
        firmware = struct.pack('<IIII', 0x20001000, ASR_APP_FLASH_START + 0x101, 0, 0) + b'\x00' * 32

        report = analisar_firmware_bytes(firmware)

        self.assertFalse(report['errors'])
        self.assertEqual(report['vectors'][0]['name'], 'MSP')
        self.assertTrue(report['vectors'][0]['target_in_sram'])
        self.assertTrue(report['vectors'][1]['thumb'])

    def test_firmware_analysis_reports_invalid_vector_table(self):
        firmware = struct.pack('<IIII', 0x10000000, ASR_APP_FLASH_START + 0x100, 0, 0)

        report = analisar_firmware_bytes(firmware)

        self.assertTrue(report['errors'])
        self.assertTrue(any('MSP' in item for item in report['errors']))

    def test_firmware_analysis_respects_custom_base_address(self):
        custom_base = 0x10000000
        firmware = struct.pack('<IIII', 0x20001000, custom_base + 0x101, 0, 0)

        report = analisar_firmware_bytes(firmware, base_address=custom_base)

        self.assertFalse(report['errors'])
        self.assertTrue(report['vectors'][1]['target_in_app'])

    def test_preflight_reports_files_crc_warnings_and_overlaps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app1 = Path(temp_dir) / 'app1.bin'
            app2 = Path(temp_dir) / 'app2.bin'
            app1.write_bytes(b'A' * 16)
            app2.write_bytes(b'B' * 16)

            report = montar_preflight_flash([
                '0x08000000',
                str(app1),
                '0x08000008',
                str(app2),
            ])

        self.assertEqual(len(report['items']), 2)
        self.assertTrue(any('overlap' in item for item in report['errors']))

    def test_firmware_inspect_json_cli_returns_nonzero_for_structural_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            firmware = Path(temp_dir) / 'bad.bin'
            firmware.write_bytes(b'\x00' * 16)

            exit_code, stdout, stderr = run_main(['firmware_inspect', str(firmware), '--json'])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr, '')
        report = json.loads(stdout)
        self.assertTrue(report['errors'])

    def test_preflight_json_cli_validates_plan_without_hardware(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            firmware = Path(temp_dir) / 'app.bin'
            firmware.write_bytes(struct.pack('<IIII', 0x20001000, ASR_APP_FLASH_START + 1, 0, 0))

            exit_code, stdout, stderr = run_main(['preflight', '0x08000000', str(firmware), '--json'])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, '')
        report = json.loads(stdout)
        self.assertEqual(report['total_size'], 16)
        self.assertEqual(report['errors'], [])

    def test_doctor_json_reports_environment_and_probe_success_with_fake_bootloader(self):
        fake = FakeBootloaderSerial()

        with mock.patch('src.cli.get_lista_portas_info', return_value=[{
            'device': 'COM1',
            'name': 'COM1',
            'description': 'CP2102',
            'hwid': 'USB',
            'vid': 0x10C4,
            'pid': 0xEA60,
            'serial_number': 'ABC',
            'location': None,
            'manufacturer': 'Silabs',
            'product': 'CP2102',
            'interface': None,
        }]):
            with mock.patch('src.ASRLoader.SerialPort', return_value=fake):
                exit_code, stdout, stderr = run_main(['-p', 'COM1', '--no-auto-boot', 'doctor', '--probe', '--json'])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, '')
        report = json.loads(stdout)
        self.assertTrue(any(item['name'] == 'probe_bootloader' and item['status'] == 'pass'
                            for item in report['checks']))

    def test_probe_sweep_json_uses_fake_bootloader(self):
        fakes = []

        def fake_serial_factory(*_args, **_kwargs):
            fake = FakeBootloaderSerial()
            fakes.append(fake)
            return fake

        with mock.patch('src.ASRLoader.SerialPort', side_effect=fake_serial_factory):
            with mock.patch('src.ASRLoader.time.sleep'):
                exit_code, stdout, stderr = run_main([
                    '-p',
                    'COM1',
                    'probe',
                    '--sweep',
                    '--sweep-bauds',
                    '115200',
                    '--sweep-reset-delays',
                    '0',
                    '--sweep-release-delays',
                    '0',
                    '--json',
                ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, '')
        report = json.loads(stdout)
        self.assertEqual(len(report['results']), 1)
        self.assertTrue(report['results'][0]['ok'])
        self.assertTrue(fakes)

    def test_snapshot_json_reads_profile_with_fake_bootloader(self):
        registers = {
            ASR_APP_FLASH_START: 0x20001000,
            ASR_APP_FLASH_START + 4: ASR_APP_FLASH_START + 0x101,
        }

        with mock.patch('src.ASRLoader.SerialPort', return_value=FakeBootloaderSerial(registers=registers)):
            exit_code, stdout, stderr = run_main(['-p', 'COM1', '--no-auto-boot', 'snapshot', '--json'])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, '')
        report = json.loads(stdout)
        self.assertEqual(report['profile'], 'asr6601')
        self.assertTrue(report['registers'][0]['ok'])
        self.assertEqual(report['registers'][0]['value'], 0x20001000)

    def test_trace_json_records_serial_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / 'trace.jsonl'
            with mock.patch('src.ASRLoader.SerialPort', return_value=FakeBootloaderSerial()):
                exit_code, _stdout, stderr = run_main([
                    '-p',
                    'COM1',
                    '--no-auto-boot',
                    '--trace-json',
                    str(trace_path),
                    'probe',
                    '--json',
                ])
            lines = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines()]

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, '')
        events = [line['event'] for line in lines]
        self.assertIn('serial_tx', events)
        self.assertIn('serial_result', events)
        serial_result = next(line for line in lines if line['event'] == 'serial_result')
        self.assertEqual(serial_result['rx_status'], 0)
        self.assertIn('duration_ms', serial_result)


if __name__ == '__main__':
    unittest.main()
