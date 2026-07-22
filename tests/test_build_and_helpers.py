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


class BuildAndHelperTests(unittest.TestCase):
    def test_extrair_versao_reads_version_from_entrypoint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                Path('asr_loader.py').write_text('VERSAO_GRAVADOR = "2.5"\n', encoding='utf-8')
                with contextlib.redirect_stdout(io.StringIO()):
                    version = build.extrair_versao()
            finally:
                os.chdir(old_cwd)

        self.assertEqual(version, '2.5')

    def test_executar_comando_returns_true_on_success(self):
        with mock.patch('build.subprocess.run') as run_mock:
            with contextlib.redirect_stdout(io.StringIO()):
                result = build.executar_comando('echo ok', 'teste')

        self.assertTrue(result)
        run_mock.assert_called_once_with('echo ok', shell=True, check=True, capture_output=True, text=True)

    def test_executar_comando_returns_false_on_called_process_error(self):
        error = subprocess.CalledProcessError(1, 'cmd', stderr='falha')

        with mock.patch('build.subprocess.run', side_effect=error):
            with contextlib.redirect_stdout(io.StringIO()):
                result = build.executar_comando('cmd', 'teste')

        self.assertFalse(result)

    def test_remover_pasta_seguro_removes_files_and_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'artifact.spec'
            dir_path = Path(temp_dir) / 'build'
            nested_file = dir_path / 'cache.txt'
            file_path.write_text('spec', encoding='utf-8')
            dir_path.mkdir()
            nested_file.write_text('cache', encoding='utf-8')

            with contextlib.redirect_stdout(io.StringIO()):
                removed_file = build.remover_pasta_seguro(str(file_path))
                removed_dir = build.remover_pasta_seguro(str(dir_path))
                removed_missing = build.remover_pasta_seguro(str(Path(temp_dir) / 'missing'))

            self.assertTrue(removed_file)
            self.assertTrue(removed_dir)
            self.assertTrue(removed_missing)
            self.assertFalse(file_path.exists())
            self.assertFalse(dir_path.exists())

    def test_run_flash_command_builds_expected_subprocess_call(self):
        completed = SimpleNamespace(returncode=0, stdout='ok', stderr='')

        with mock.patch('test_flash.subprocess.run', return_value=completed) as run_mock:
            with contextlib.redirect_stdout(io.StringIO()):
                result = test_flash.run_flash_command('0x08000000', 'app.bin', port='COM5', baud=115200)

        self.assertTrue(result)
        run_mock.assert_called_once()
        command = run_mock.call_args.args[0]
        self.assertEqual(command, [
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

    def test_run_flash_command_returns_false_on_nonzero_exit(self):
        completed = SimpleNamespace(returncode=2, stdout='', stderr='erro')

        with mock.patch('test_flash.subprocess.run', return_value=completed):
            with contextlib.redirect_stdout(io.StringIO()):
                result = test_flash.run_flash_command('0x08000000', 'app.bin')

        self.assertFalse(result)

    def test_asr_monitor_search_for_ports_delegates_to_pyserial(self):
        ports = [SimpleNamespace(device='COM1')]

        with mock.patch('asr_monitor.serial.tools.list_ports.comports', return_value=ports):
            self.assertEqual(asr_monitor.search_for_ports(), ports)


if __name__ == '__main__':
    unittest.main()
