import contextlib
import io
import json
import unittest
from unittest import mock

from src.cli import cli_build_parser, main


class TestesDoAnalisadorCli(unittest.TestCase):
    def setUp(self):
        self.analisador = cli_build_parser()

    def test_comando_testeboot_esta_registrado(self):
        argumentos = self.analisador.parse_args(['testeboot'])
        self.assertEqual(argumentos.command, 'testeboot')

    def test_comando_clear_eeprom_esta_registrado(self):
        argumentos = self.analisador.parse_args(['clear_eeprom'])
        self.assertEqual(argumentos.command, 'clear_eeprom')

    def test_comando_de_linha_de_controle_aceita_tempo_de_retencao(self):
        argumentos = self.analisador.parse_args(['dtr1', '--hold', '0.5'])
        self.assertEqual(argumentos.command, 'dtr1')
        self.assertEqual(argumentos.control_line, 'dtr')
        self.assertFalse(argumentos.control_state)
        self.assertEqual(argumentos.hold, 0.5)

    def test_opcoes_globais_de_boot_automatico_e_log_sao_analisadas(self):
        argumentos = self.analisador.parse_args([
            '--no-auto-boot',
            '--boot-reset-delay',
            '0.25',
            '--boot-release-delay',
            '0.5',
            '--log-file',
            'debug.log',
            'testeboot',
        ])

        self.assertTrue(argumentos.no_auto_boot)
        self.assertEqual(argumentos.boot_reset_delay, 0.25)
        self.assertEqual(argumentos.boot_release_delay, 0.5)
        self.assertEqual(argumentos.log_file, 'debug.log')

    def test_alias_dts_nao_esta_registrado(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.analisador.parse_args(['dts1'])

    def test_comdiag_json_retorna_json_valido_sem_conexao_com_hardware(self):
        saida_padrao = io.StringIO()
        saida_de_erro = io.StringIO()

        with mock.patch('src.cli.get_lista_portas_info', return_value=[]):
            with contextlib.redirect_stdout(saida_padrao), contextlib.redirect_stderr(
                saida_de_erro
            ):
                codigo_de_saida = main(['comdiag', '--json'])

        self.assertEqual(codigo_de_saida, 0)
        diagnostico = json.loads(saida_padrao.getvalue())
        self.assertEqual(diagnostico['app'], 'ASR Loader')
        self.assertIn('python', diagnostico)
        self.assertEqual(diagnostico['ports'], [])
        self.assertEqual(saida_de_erro.getvalue(), '')

    def test_tempo_de_boot_negativo_retorna_codigo_diferente_de_zero(self):
        saida_padrao = io.StringIO()
        saida_de_erro = io.StringIO()

        with contextlib.redirect_stdout(saida_padrao), contextlib.redirect_stderr(
            saida_de_erro
        ):
            codigo_de_saida = main(['--boot-reset-delay', '-0.1', 'testeboot'])

        self.assertEqual(codigo_de_saida, 1)
        self.assertIn('tempos de boot automatico', saida_de_erro.getvalue())

    def test_falha_em_comando_local_retorna_codigo_diferente_de_zero(self):
        saida_padrao = io.StringIO()
        saida_de_erro = io.StringIO()
        with contextlib.redirect_stdout(saida_padrao), contextlib.redirect_stderr(
            saida_de_erro
        ):
            codigo_de_saida = main(['ota_pack', 'arquivo_inexistente.bin'])

        self.assertEqual(codigo_de_saida, 1)
        self.assertIn('arquivo nao encontrado', saida_de_erro.getvalue())


if __name__ == '__main__':
    unittest.main()
