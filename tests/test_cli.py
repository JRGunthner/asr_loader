import contextlib
import io
import json
import unittest
from unittest import mock

from src.cli import cli_build_parser, main


class CliParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = cli_build_parser()

    def test_probe_command_is_registered(self):
        args = self.parser.parse_args(['probe'])
        self.assertEqual(args.command, 'probe')

    def test_clear_eeprom_command_is_registered(self):
        args = self.parser.parse_args(['clear_eeprom'])
        self.assertEqual(args.command, 'clear_eeprom')

    def test_control_line_command_accepts_hold(self):
        args = self.parser.parse_args(['dtr1', '--hold', '0.5'])
        self.assertEqual(args.command, 'dtr1')
        self.assertEqual(args.control_line, 'dtr')
        self.assertTrue(args.control_state)
        self.assertEqual(args.hold, 0.5)

    def test_global_auto_boot_and_log_options_are_parsed(self):
        args = self.parser.parse_args([
            '--no-auto-boot',
            '--boot-reset-delay',
            '0.25',
            '--boot-release-delay',
            '0.5',
            '--log-file',
            'debug.log',
            'probe',
        ])

        self.assertTrue(args.no_auto_boot)
        self.assertEqual(args.boot_reset_delay, 0.25)
        self.assertEqual(args.boot_release_delay, 0.5)
        self.assertEqual(args.log_file, 'debug.log')

    def test_dts_alias_is_not_registered(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parser.parse_args(['dts1'])

    def test_diag_json_returns_valid_json_without_hardware_connection(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with mock.patch('src.cli.get_lista_portas_info', return_value=[]):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main(['diag', '--json'])

        self.assertEqual(exit_code, 0)
        diagnostic = json.loads(stdout.getvalue())
        self.assertEqual(diagnostic['app'], 'ASR Loader')
        self.assertIn('python', diagnostic)
        self.assertEqual(diagnostic['ports'], [])
        self.assertEqual(stderr.getvalue(), '')

    def test_negative_boot_timing_returns_nonzero(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(['--boot-reset-delay', '-0.1', 'probe'])

        self.assertEqual(exit_code, 1)
        self.assertIn('tempos de boot automatico', stderr.getvalue())

    def test_local_command_failure_returns_nonzero(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(['ota_pack', 'arquivo_inexistente.bin'])

        self.assertEqual(exit_code, 1)
        self.assertIn('arquivo nao encontrado', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
