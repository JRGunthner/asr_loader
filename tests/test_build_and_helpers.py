import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import asr_monitor
import build
import test_flash


class TestesDeBuildEAuxiliares(unittest.TestCase):
    def test_extrair_versao_le_versao_do_ponto_de_entrada(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            diretorio_atual_anterior = os.getcwd()
            try:
                os.chdir(diretorio_temporario)
                Path('asr_loader.py').write_text('VERSAO_GRAVADOR = "2.5"\n', encoding='utf-8')
                with contextlib.redirect_stdout(io.StringIO()):
                    versao = build.extrair_versao()
            finally:
                os.chdir(diretorio_atual_anterior)

        self.assertEqual(versao, '2.5')

    def test_executar_comando_retorna_verdadeiro_em_caso_de_sucesso(self):
        with mock.patch('build.subprocess.run') as executar_simulado:
            with contextlib.redirect_stdout(io.StringIO()):
                resultado = build.executar_comando('echo ok', 'teste')

        self.assertTrue(resultado)
        executar_simulado.assert_called_once_with(
            'echo ok', shell=True, check=True, capture_output=True, text=True
        )

    def test_executar_comando_retorna_falso_em_caso_de_erro_no_processo(self):
        erro = subprocess.CalledProcessError(1, 'cmd', stderr='falha')

        with mock.patch('build.subprocess.run', side_effect=erro):
            with contextlib.redirect_stdout(io.StringIO()):
                resultado = build.executar_comando('cmd', 'teste')

        self.assertFalse(resultado)

    def test_remover_pasta_seguro_remove_arquivos_e_diretorios(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            caminho_arquivo = Path(diretorio_temporario) / 'artifact.spec'
            caminho_diretorio = Path(diretorio_temporario) / 'build'
            arquivo_aninhado = caminho_diretorio / 'cache.txt'
            caminho_arquivo.write_text('spec', encoding='utf-8')
            caminho_diretorio.mkdir()
            arquivo_aninhado.write_text('cache', encoding='utf-8')

            with contextlib.redirect_stdout(io.StringIO()):
                arquivo_removido = build.remover_pasta_seguro(str(caminho_arquivo))
                diretorio_removido = build.remover_pasta_seguro(str(caminho_diretorio))
                ausente_removido = build.remover_pasta_seguro(
                    str(Path(diretorio_temporario) / 'missing')
                )

            self.assertTrue(arquivo_removido)
            self.assertTrue(diretorio_removido)
            self.assertTrue(ausente_removido)
            self.assertFalse(caminho_arquivo.exists())
            self.assertFalse(caminho_diretorio.exists())

    def test_comando_de_flash_monta_chamada_de_subprocesso_esperada(self):
        processo_concluido = SimpleNamespace(returncode=0, stdout='ok', stderr='')

        with mock.patch(
            'test_flash.subprocess.run', return_value=processo_concluido
        ) as executar_simulado:
            with contextlib.redirect_stdout(io.StringIO()):
                resultado = test_flash.run_flash_command(
                    '0x08000000', 'app.bin', port='COM5', baud=115200
                )

        self.assertTrue(resultado)
        executar_simulado.assert_called_once()
        comando = executar_simulado.call_args.args[0]
        self.assertEqual(comando, [
            'python',
            'asr_loader.py',
            '--port',
            'COM5',
            '--baud',
            '115200',
            'flash',
            '0x08000000',
            'app.bin',
        ])

    def test_comando_de_flash_retorna_falso_quando_saida_nao_e_zero(self):
        processo_concluido = SimpleNamespace(returncode=2, stdout='', stderr='erro')

        with mock.patch('test_flash.subprocess.run', return_value=processo_concluido):
            with contextlib.redirect_stdout(io.StringIO()):
                resultado = test_flash.run_flash_command('0x08000000', 'app.bin')

        self.assertFalse(resultado)

    def test_monitor_asr_delega_busca_de_portas_ao_pyserial(self):
        portas = [SimpleNamespace(device='COM1')]

        with mock.patch('asr_monitor.list_ports.comports', return_value=portas):
            self.assertEqual(asr_monitor.buscar_portas_com(), portas)


if __name__ == '__main__':
    unittest.main()
