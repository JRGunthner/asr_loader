import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.comandos import (
    asr_apagar_eeprom,
    asr_conectar,
    asr_controlar_linha_serial,
    asr_endereco_em_faixa_app,
    asr_endereco_em_sram,
    asr_fechar_porta,
    asr_formatar_hexdump,
    asr_hw_reset,
    asr_ler_mem,
)
from src.constantes import EEPROM_ENDERECO_ASR6601CB, EEPROM_ENDERECO_ASR6601SE, EEPROM_SIZE
from src.exceptions import CmdExcessao


class SerialDeFechamentoSimulada:
    def __init__(self, falhar_ao_fechar=False):
        self.falhar_ao_fechar = falhar_ao_fechar
        self.fechada = False

    def close(self):
        self.fechada = True
        if self.falhar_ao_fechar:
            raise OSError('already gone')


class ProcessadorSimulado:
    def __init__(
        self,
        portas_com_falha_de_conexao=None,
        enderecos_com_falha_de_apagamento=None,
        valores_de_registradores=None,
    ):
        self.ser = None
        self.porta_atual = None
        self.portas = []
        self.portas_conectadas = []
        self.baudrates = []
        self.estados_dtr = []
        self.estados_rts = []
        self.modos_de_reset = []
        self.chamadas_de_apagamento = []
        self.leituras_de_registradores = []
        self.portas_com_falha_de_conexao = set(portas_com_falha_de_conexao or [])
        self.enderecos_com_falha_de_apagamento = set(
            enderecos_com_falha_de_apagamento or []
        )
        self.valores_de_registradores = dict(valores_de_registradores or {})

    def set_port(self, port, baud=None):
        self.porta_atual = port
        self.portas.append((port, baud))
        self.ser = SerialDeFechamentoSimulada()

    def conectar(self):
        self.portas_conectadas.append(self.porta_atual)
        if self.porta_atual in self.portas_com_falha_de_conexao:
            raise Exception('connect failed')

    def set_baudrate(self, baud):
        self.baudrates.append(baud)

    def erase(self, address, size):
        self.chamadas_de_apagamento.append((address, size))
        if address in self.enderecos_com_falha_de_apagamento:
            raise Exception('erase failed')

    def ler_reg(self, address):
        self.leituras_de_registradores.append(address)
        return (self.valores_de_registradores[address],)

    def set_dtr(self, state):
        self.estados_dtr.append(state)

    def set_rts(self, state):
        self.estados_rts.append(state)

    def hw_reset(self, mode):
        self.modos_de_reset.append(mode)


class TestesDaLogicaDosComandos(unittest.TestCase):
    def test_asr_fechar_porta_fecha_e_limpa_serial(self):
        processador = SimpleNamespace(ser=SerialDeFechamentoSimulada())

        asr_fechar_porta(processador)

        self.assertIsNone(processador.ser)

    def test_asr_fechar_porta_ignora_erro_do_sistema_ao_fechar(self):
        processador = SimpleNamespace(ser=SerialDeFechamentoSimulada(falhar_ao_fechar=True))

        asr_fechar_porta(processador)

        self.assertIsNone(processador.ser)

    def test_asr_conectar_tenta_portas_em_ordem_inversa_ate_obter_sucesso(self):
        processador = ProcessadorSimulado(portas_com_falha_de_conexao={'COM2'})

        with contextlib.redirect_stdout(io.StringIO()):
            resultado = asr_conectar(processador, ['COM1', 'COM2'], 115200)

        self.assertTrue(resultado)
        self.assertEqual(processador.portas_conectadas, ['COM2', 'COM1'])
        self.assertEqual(processador.baudrates, [115200])

    def test_asr_conectar_lanca_excecao_quando_nao_ha_portas_disponiveis(self):
        with self.assertRaisesRegex(CmdExcessao, 'nenhuma porta serial'):
            asr_conectar(ProcessadorSimulado(), [], 115200)

    def test_asr_conectar_lanca_excecao_apos_falha_em_todas_as_portas(self):
        processador = ProcessadorSimulado(portas_com_falha_de_conexao={'COM1', 'COM2'})

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(CmdExcessao, 'nao foi possivel conectar'):
                asr_conectar(processador, ['COM1', 'COM2'], 115200)

        self.assertEqual(processador.portas_conectadas, ['COM2', 'COM1'])

    def test_hexdump_formata_endereco_hexadecimal_e_ascii(self):
        hexdump = asr_formatar_hexdump(0x20000000, b'ABC\x00\xff')

        self.assertIn('20000000', hexdump)
        self.assertIn('41 42 43 00 FF', hexdump)
        self.assertIn('|ABC..|', hexdump)

    def test_auxiliares_de_faixa_de_enderecos_cobrem_limites(self):
        self.assertTrue(asr_endereco_em_faixa_app(0x08000000))
        self.assertTrue(asr_endereco_em_faixa_app(0x0803FFFF))
        self.assertFalse(asr_endereco_em_faixa_app(0x08040000))
        self.assertTrue(asr_endereco_em_sram(0x20000000))
        self.assertTrue(asr_endereco_em_sram(0x3FFFFFFF))
        self.assertFalse(asr_endereco_em_sram(0x40000000))

    def test_ler_mem_le_palavras_alinhadas_e_retorna_fatia_solicitada(self):
        processador = ProcessadorSimulado(valores_de_registradores={
            0x20000000: 0x04030201,
            0x20000004: 0x08070605,
        })
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(address=0x20000001, size=5, baud=921600, output=None)

        with contextlib.redirect_stdout(io.StringIO()):
            dados = asr_ler_mem(parametros, processador, configuracao)

        self.assertEqual(dados, b'\x02\x03\x04\x05\x06')
        self.assertEqual(processador.leituras_de_registradores, [0x20000000, 0x20000004])

    def test_ler_mem_pode_escrever_dados_brutos_em_arquivo(self):
        processador = ProcessadorSimulado(
            valores_de_registradores={0x20000000: 0x04030201}
        )
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])

        with tempfile.TemporaryDirectory() as diretorio_temporario:
            arquivo_de_saida = Path(diretorio_temporario) / 'dump.bin'
            parametros = SimpleNamespace(
                address=0x20000000, size=4, baud=921600, output=str(arquivo_de_saida)
            )
            with contextlib.redirect_stdout(io.StringIO()):
                dados = asr_ler_mem(parametros, processador, configuracao)
            self.assertEqual(arquivo_de_saida.read_bytes(), dados)

        self.assertEqual(dados, b'\x01\x02\x03\x04')

    def test_ler_mem_rejeita_tamanho_nao_positivo_antes_de_conectar(self):
        processador = ProcessadorSimulado()
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(address=0x20000000, size=0, baud=921600, output=None)

        with self.assertRaisesRegex(Exception, 'tamanho'):
            asr_ler_mem(parametros, processador, configuracao)

        self.assertEqual(processador.portas, [])

    def test_apagar_eeprom_detecta_variante_bem_sucedida(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_apagamento={EEPROM_ENDERECO_ASR6601CB}
        )

        saida_padrao = io.StringIO()
        with contextlib.redirect_stdout(saida_padrao):
            asr_apagar_eeprom(processador)

        self.assertEqual(processador.chamadas_de_apagamento, [
            (EEPROM_ENDERECO_ASR6601CB, EEPROM_SIZE),
            (EEPROM_ENDERECO_ASR6601SE, EEPROM_SIZE),
        ])
        self.assertIn('ASR6601SE', saida_padrao.getvalue())

    def test_apagar_eeprom_lanca_excecao_quando_todos_os_mapeamentos_falham(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_apagamento={
                EEPROM_ENDERECO_ASR6601CB,
                EEPROM_ENDERECO_ASR6601SE,
            }
        )

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(Exception, 'todos os mapeamentos'):
                asr_apagar_eeprom(processador)

    def test_controlar_linha_serial_define_dtr_e_fecha_porta(self):
        processador = ProcessadorSimulado()
        configuracao = SimpleNamespace(portas_disponiveis=['COM3'])
        parametros = SimpleNamespace(baud=57600, control_line='dtr', control_state=True, hold=0)

        with contextlib.redirect_stdout(io.StringIO()):
            resultado = asr_controlar_linha_serial(parametros, processador, configuracao)

        self.assertTrue(resultado)
        self.assertEqual(processador.portas, [('COM3', 57600)])
        self.assertEqual(processador.estados_dtr, [True])
        self.assertEqual(processador.estados_rts, [])
        self.assertIsNone(processador.ser)

    def test_controlar_linha_serial_rejeita_tempo_de_retencao_negativo(self):
        processador = ProcessadorSimulado()
        configuracao = SimpleNamespace(portas_disponiveis=['COM3'])
        parametros = SimpleNamespace(baud=57600, control_line='dtr', control_state=True, hold=-1)

        with self.assertRaisesRegex(Exception, '--hold'):
            asr_controlar_linha_serial(parametros, processador, configuracao)

        self.assertEqual(processador.portas, [])

    def test_reset_de_hardware_usa_porta_selecionada_e_fecha_apos_pulso(self):
        processador = ProcessadorSimulado()
        configuracao = SimpleNamespace(portas_disponiveis=['COM4'])
        parametros = SimpleNamespace(baud=115200, boot=True)

        with contextlib.redirect_stdout(io.StringIO()):
            resultado = asr_hw_reset(parametros, processador, configuracao)

        self.assertTrue(resultado)
        self.assertEqual(processador.portas, [('COM4', 115200)])
        self.assertEqual(processador.modos_de_reset, [1])
        self.assertIsNone(processador.ser)


if __name__ == '__main__':
    unittest.main()
