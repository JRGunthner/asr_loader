import contextlib
import io
import unittest

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

    def test_dts_alias_is_not_registered(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parser.parse_args(['dts1'])

    def test_local_command_failure_returns_nonzero(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(['ota_pack', 'arquivo_inexistente.bin'])

        self.assertEqual(exit_code, 1)
        self.assertIn('arquivo nao encontrado', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
