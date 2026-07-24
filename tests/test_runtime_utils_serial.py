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


class SerialDeEstiloNovo:
    def __init__(self):
        self.port = 'COM7'
        self.baudrate = 115200
        self.chamadas = []
        self.dados_de_leitura = b'ab'
        self.fechada = False

    def read(self, size):
        self.chamadas.append(('read', size))
        return self.dados_de_leitura[:size]

    def write(self, data):
        self.chamadas.append(('write', data))
        return len(data)

    def close(self):
        self.fechada = True
        self.chamadas.append(('close',))

    def setDTR(self, estado):
        self.chamadas.append(('setDTR', estado))

    def setRTS(self, estado):
        self.chamadas.append(('setRTS', estado))

    def reset_input_buffer(self):
        self.chamadas.append(('reset_input_buffer',))

    def reset_output_buffer(self):
        self.chamadas.append(('reset_output_buffer',))


class SerialDeEstiloAntigo:
    def __init__(self):
        self.port = 'COM8'
        self.baudrate = 9600
        self.dtr = None
        self.rts = None
        self.chamadas = []

    def read(self, size):
        self.chamadas.append(('read', size))
        return b''

    def write(self, data):
        self.chamadas.append(('write', data))
        return len(data)

    def close(self):
        self.chamadas.append(('close',))

    def flushInput(self):
        self.chamadas.append(('flushInput',))

    def flushOutput(self):
        self.chamadas.append(('flushOutput',))


class TestesDoRuntimeDosUtilitariosESerial(unittest.TestCase):
    def test_configuracao_de_execucao_escreve_e_fecha_arquivo_de_log(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            caminho_do_log = Path(diretorio_temporario) / 'logs' / 'run.log'

            configuracao = RuntimeConfig(log_file=caminho_do_log)
            configuracao.log('evento de teste')
            configuracao.close_log()
            configuracao.close_log()

            conteudo = caminho_do_log.read_text(encoding='utf-8')

        self.assertIn('--- inicio do log ---', conteudo)
        self.assertIn('evento de teste', conteudo)
        self.assertIn('--- fim do log ---', conteudo)
        self.assertIsNone(configuracao._log_handle)

    def test_arg_int_aceita_decimal_e_hexadecimal(self):
        self.assertEqual(arg_int('16'), 16)
        self.assertEqual(arg_int('0x10'), 16)

    def test_obter_crc32_le_conteudo_do_arquivo(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            caminho = Path(diretorio_temporario) / 'fw.bin'
            caminho.write_bytes(b'abc123')

            crc = get_crc32(caminho)

        self.assertEqual(crc, zlib.crc32(b'abc123') & 0xFFFFFFFF)

    def test_lista_de_portas_seriais_esta_ordenada(self):
        portas = [
            SimpleNamespace(device='COM9'),
            SimpleNamespace(device='COM1'),
            SimpleNamespace(device='COM3'),
        ]

        with mock.patch('src.utils.list_ports.comports', return_value=portas):
            self.assertEqual(get_lista_portas_com(), ['COM1', 'COM3', 'COM9'])

    def test_informacoes_das_portas_seriais_incluem_campos_de_diagnostico(self):
        portas = [
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

        with mock.patch('src.utils.list_ports.comports', return_value=portas):
            informacoes = get_lista_portas_info()

        self.assertEqual([item['device'] for item in informacoes], ['COM1', 'COM2'])
        self.assertEqual(informacoes[1]['description'], 'CP2102 USB UART')
        self.assertEqual(informacoes[1]['vid'], 0x10C4)
        self.assertEqual(informacoes[1]['pid'], 0xEA60)
        self.assertEqual(informacoes[1]['serial_number'], 'ABC')

    def test_obter_dispositivo_conectado_imprime_portas_em_ordem_inversa(self):
        saida_padrao = io.StringIO()

        with contextlib.redirect_stdout(saida_padrao):
            get_dispositivo_conectado(['COM1', 'COM2'])

        self.assertEqual(
            saida_padrao.getvalue().splitlines(),
            ['Serial port COM2', 'Serial port COM1'],
        )

    def test_porta_serial_delega_para_nova_api_do_pyserial(self):
        serial_simulada = SerialDeEstiloNovo()

        with mock.patch(
            'src.serial_port.serial.Serial', return_value=serial_simulada
        ) as construtor_serial:
            porta = SerialPort('COM7', 115200, timeout=3)
            self.assertEqual(porta.port, 'COM7')
            self.assertEqual(porta.baudrate, 115200)
            porta.baudrate = 57600
            self.assertEqual(porta.baudrate, 57600)
            self.assertEqual(porta.read(1), b'a')
            self.assertEqual(porta.write(b'xy'), 2)
            porta.set_dtr(True)
            porta.set_rts(False)
            porta.flush_input()
            porta.flush_output()
            porta.close()

        construtor_serial.assert_called_once_with('COM7', 115200, timeout=3)
        self.assertIn(('setDTR', True), serial_simulada.chamadas)
        self.assertIn(('setRTS', False), serial_simulada.chamadas)
        self.assertIn(('reset_input_buffer',), serial_simulada.chamadas)
        self.assertIn(('reset_output_buffer',), serial_simulada.chamadas)
        self.assertTrue(serial_simulada.fechada)

    def test_porta_serial_recua_para_api_antiga_do_pyserial(self):
        serial_simulada = SerialDeEstiloAntigo()

        with mock.patch('src.serial_port.serial.Serial', return_value=serial_simulada):
            porta = SerialPort('COM8', 9600, timeout=1)
            porta.set_dtr(False)
            porta.set_rts(True)
            porta.flush_input()
            porta.flush_output()

        self.assertFalse(serial_simulada.dtr)
        self.assertTrue(serial_simulada.rts)
        self.assertIn(('flushInput',), serial_simulada.chamadas)
        self.assertIn(('flushOutput',), serial_simulada.chamadas)


if __name__ == '__main__':
    unittest.main()
