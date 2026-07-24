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
from src.diagnosticos import analisar_firmware_bytes, montar_prevalidar_flash, parse_csv_floats, parse_csv_ints

from tests.fake_bootloader import FakeBootloaderSerial


def executar_principal(argumentos):
    saida_padrao = io.StringIO()
    saida_de_erro = io.StringIO()
    with contextlib.redirect_stdout(saida_padrao), contextlib.redirect_stderr(saida_de_erro):
        codigo_de_saida = main(argumentos)
    return codigo_de_saida, saida_padrao.getvalue(), saida_de_erro.getvalue()


class TestesDosRecursosDeDiagnostico(unittest.TestCase):
    def test_analisador_registra_novos_comandos_de_diagnostico(self):
        analisador = cli_build_parser()

        self.assertEqual(analisador.parse_args(['doctor']).command, 'doctor')
        self.assertEqual(analisador.parse_args(['snapshot']).command, 'snapshot')
        self.assertEqual(analisador.parse_args(['firmware_inspect', 'app.bin']).command, 'firmware_inspect')
        self.assertEqual(analisador.parse_args(['prevalidar', '0x08000000', 'app.bin']).command, 'prevalidar')

    def test_analisadores_csv_aceitam_decimal_hexadecimal_e_rejeitam_valores_vazios(self):
        self.assertEqual(parse_csv_floats('0,0.1,0.2'), [0.0, 0.1, 0.2])
        self.assertEqual(parse_csv_ints('115200,0xE1000'), [115200, 921600])
        with self.assertRaises(ValueError):
            parse_csv_floats('')
        with self.assertRaises(ValueError):
            parse_csv_ints('0')

    def test_analise_de_firmware_detecta_tabela_de_vetores_valida(self):
        firmware = struct.pack('<IIII', 0x20001000, ASR_APP_FLASH_START + 0x101, 0, 0) + b'\x00' * 32

        relatorio = analisar_firmware_bytes(firmware)

        self.assertFalse(relatorio['errors'])
        self.assertEqual(relatorio['vectors'][0]['name'], 'MSP')
        self.assertTrue(relatorio['vectors'][0]['target_in_sram'])
        self.assertTrue(relatorio['vectors'][1]['thumb'])

    def test_analise_de_firmware_informa_tabela_de_vetores_invalida(self):
        firmware = struct.pack('<IIII', 0x10000000, ASR_APP_FLASH_START + 0x100, 0, 0)

        relatorio = analisar_firmware_bytes(firmware)

        self.assertTrue(relatorio['errors'])
        self.assertTrue(any('MSP' in item for item in relatorio['errors']))

    def test_analise_de_firmware_respeita_endereco_base_personalizado(self):
        base_personalizada = 0x10000000
        firmware = struct.pack('<IIII', 0x20001000, base_personalizada + 0x101, 0, 0)

        relatorio = analisar_firmware_bytes(firmware, base_address=base_personalizada)

        self.assertFalse(relatorio['errors'])
        self.assertTrue(relatorio['vectors'][1]['target_in_app'])

    def test_prevalidacao_detecta_avisos_de_crc_e_sobreposicoes(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            aplicativo_1 = Path(diretorio_temporario) / 'app1.bin'
            aplicativo_2 = Path(diretorio_temporario) / 'app2.bin'
            aplicativo_1.write_bytes(b'A' * 16)
            aplicativo_2.write_bytes(b'B' * 16)

            relatorio = montar_prevalidar_flash([
                '0x08000000',
                str(aplicativo_1),
                '0x08000008',
                str(aplicativo_2),
            ])

        self.assertEqual(len(relatorio['items']), 2)
        self.assertTrue(any('overlap' in item for item in relatorio['errors']))

    def test_cli_de_inspecao_de_firmware_retorna_nao_zero_para_erros_estruturais(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            firmware = Path(diretorio_temporario) / 'bad.bin'
            firmware.write_bytes(b'\x00' * 16)

            codigo_de_saida, saida_padrao, saida_de_erro = executar_principal(
                ['firmware_inspect', str(firmware), '--json']
            )

        self.assertEqual(codigo_de_saida, 1)
        self.assertEqual(saida_de_erro, '')
        relatorio = json.loads(saida_padrao)
        self.assertTrue(relatorio['errors'])

    def test_cli_prevalidar_json_verifica_plano_sem_hardware(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            firmware = Path(diretorio_temporario) / 'app.bin'
            firmware.write_bytes(struct.pack('<IIII', 0x20001000, ASR_APP_FLASH_START + 1, 0, 0))

            codigo_de_saida, saida_padrao, saida_de_erro = executar_principal(
                ['prevalidar', '0x08000000', str(firmware), '--json']
            )

        self.assertEqual(codigo_de_saida, 0)
        self.assertEqual(saida_de_erro, '')
        relatorio = json.loads(saida_padrao)
        self.assertEqual(relatorio['total_size'], 16)
        self.assertEqual(relatorio['errors'], [])

    def test_doctor_json_informa_ambiente_e_sucesso_com_bootloader_simulado(self):
        bootloader_simulado = FakeBootloaderSerial()

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
            with mock.patch('src.ASRLoader.SerialPort', return_value=bootloader_simulado):
                codigo_de_saida, saida_padrao, saida_de_erro = executar_principal(
                    ['-p', 'COM1', '--no-auto-boot', 'doctor', '--testeboot', '--json']
                )

        self.assertEqual(codigo_de_saida, 0)
        self.assertEqual(saida_de_erro, '')
        relatorio = json.loads(saida_padrao)
        self.assertTrue(any(item['name'] == 'testeboot_bootloader' and item['status'] == 'pass'
                            for item in relatorio['checks']))

    def test_varredura_testeboot_json_usa_bootloader_simulado(self):
        bootloaders_simulados = []

        def criar_serial_simulada(*_argumentos, **_argumentos_nomeados):
            bootloader_simulado = FakeBootloaderSerial()
            bootloaders_simulados.append(bootloader_simulado)
            return bootloader_simulado

        with mock.patch('src.ASRLoader.SerialPort', side_effect=criar_serial_simulada):
            with mock.patch('src.ASRLoader.time.sleep'):
                codigo_de_saida, saida_padrao, saida_de_erro = executar_principal([
                    '-p',
                    'COM1',
                    'testeboot',
                    '--sweep',
                    '--sweep-bauds',
                    '115200',
                    '--sweep-reset-delays',
                    '0',
                    '--sweep-release-delays',
                    '0',
                    '--json',
                ])

        self.assertEqual(codigo_de_saida, 0)
        self.assertEqual(saida_de_erro, '')
        relatorio = json.loads(saida_padrao)
        self.assertEqual(len(relatorio['results']), 1)
        self.assertTrue(relatorio['results'][0]['ok'])
        self.assertTrue(bootloaders_simulados)

    def test_snapshot_json_le_perfil_com_bootloader_simulado(self):
        registradores = {
            ASR_APP_FLASH_START: 0x20001000,
            ASR_APP_FLASH_START + 4: ASR_APP_FLASH_START + 0x101,
        }

        with mock.patch(
            'src.ASRLoader.SerialPort',
            return_value=FakeBootloaderSerial(registradores=registradores),
        ):
            codigo_de_saida, saida_padrao, saida_de_erro = executar_principal(
                ['-p', 'COM1', '--no-auto-boot', 'snapshot', '--json']
            )

        self.assertEqual(codigo_de_saida, 0)
        self.assertEqual(saida_de_erro, '')
        relatorio = json.loads(saida_padrao)
        self.assertEqual(relatorio['profile'], 'asr6601')
        self.assertTrue(relatorio['registers'][0]['ok'])
        self.assertEqual(relatorio['registers'][0]['value'], 0x20001000)

    def test_rastreamento_json_registra_eventos_seriais(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            caminho_do_rastreamento = Path(diretorio_temporario) / 'trace.jsonl'
            with mock.patch('src.ASRLoader.SerialPort', return_value=FakeBootloaderSerial()):
                codigo_de_saida, _saida_padrao, saida_de_erro = executar_principal([
                    '-p',
                    'COM1',
                    '--no-auto-boot',
                    '--trace-json',
                    str(caminho_do_rastreamento),
                    'testeboot',
                    '--json',
                ])
            linhas = [
                json.loads(linha)
                for linha in caminho_do_rastreamento.read_text(encoding='utf-8').splitlines()
            ]

        self.assertEqual(codigo_de_saida, 0)
        self.assertEqual(saida_de_erro, '')
        eventos = [linha['event'] for linha in linhas]
        self.assertIn('serial_tx', eventos)
        self.assertIn('serial_result', eventos)
        resultado_serial = next(
            linha for linha in linhas if linha['event'] == 'serial_result'
        )
        self.assertEqual(resultado_serial['rx_status'], 0)
        self.assertIn('duration_ms', resultado_serial)


if __name__ == '__main__':
    unittest.main()
