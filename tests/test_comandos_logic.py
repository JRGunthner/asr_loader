import contextlib
import io
import mmap
import os
import tempfile
import unittest
import struct
from pathlib import Path
from types import SimpleNamespace

from src.comandos import (
    _salvar_mapa_eeprom,
    asr_apagar_eeprom,
    asr_clean_eeprom,
    asr_conectar,
    asr_controlar_linha_serial,
    asr_endereco_em_faixa_app,
    asr_endereco_em_sram,
    asr_fechar_porta,
    asr_formatar_hexdump,
    asr_hw_reset,
    asr_identificar_mcu,
    asr_ler_mem,
    asr_mapa_memoria,
)
from src.constantes import (
    EEPROM_ENDERECO_ASR6601CB,
    EEPROM_ENDERECO_ASR6601SE,
    EEPROM_ENDERECO_V8_ASR6601CB,
    EEPROM_ENDERECO_V8_ASR6601SE,
    EEPROM_SIZE,
    EEPROM_SIZE_V8,
)
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
        enderecos_com_falha_de_leitura=None,
    ):
        self.ser = None
        self.porta_atual = None
        self.portas = []
        self.portas_conectadas = []
        self.baudrates = []
        self.estados_dtr = []
        self.estados_rts = []
        self.modos_de_reset = []
        self.modos_de_reset_software = []
        self.chamadas_de_apagamento = []
        self.leituras_de_registradores = []
        self.portas_com_falha_de_conexao = set(portas_com_falha_de_conexao or [])
        self.enderecos_com_falha_de_apagamento = set(
            enderecos_com_falha_de_apagamento or []
        )
        self.valores_de_registradores = dict(valores_de_registradores or {})
        self.enderecos_com_falha_de_leitura = set(enderecos_com_falha_de_leitura or [])

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
        if address in self.enderecos_com_falha_de_leitura:
            raise CmdExcessao('read failed')
        self.leituras_de_registradores.append(address)
        return (self.valores_de_registradores[address],)

    def set_dtr(self, state):
        self.estados_dtr.append(state)

    def set_rts(self, state):
        self.estados_rts.append(state)

    def hw_reset(self, mode):
        self.modos_de_reset.append(mode)

    def sw_reset(self, mode):
        self.modos_de_reset_software.append(mode)


class TestesDaLogicaDosComandos(unittest.TestCase):
    def test_clear_eeprom_apaga_somente_a_faixa_do_mcu_informado(self):
        for variante, v8, endereco, tamanho in (
            ('ASR6601CB', False, EEPROM_ENDERECO_ASR6601CB, EEPROM_SIZE),
            ('ASR6601SE', False, EEPROM_ENDERECO_ASR6601SE - EEPROM_SIZE, 2 * EEPROM_SIZE),
            ('ASR6601SE', True, EEPROM_ENDERECO_ASR6601SE - EEPROM_SIZE, 2 * EEPROM_SIZE),
        ):
            with self.subTest(variante=variante, v8=v8):
                processador = ProcessadorSimulado()
                parametros = SimpleNamespace(mcu=variante, baud=921600)
                configuracao = SimpleNamespace(portas_disponiveis=['COM1'], v8=v8)
                asr_clean_eeprom(parametros, processador, configuracao)
                self.assertEqual(processador.chamadas_de_apagamento, [(endereco, tamanho)])
                self.assertEqual(processador.modos_de_reset_software, [0])

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
        self.assertEqual(processador.modos_de_reset_software, [0])

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
        self.assertEqual(processador.modos_de_reset_software, [0])

    def test_ler_mem_executa_reset_apos_falha_de_leitura(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_leitura={0x20000000}
        )
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(address=0x20000000, size=4, baud=921600, output=None)

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(CmdExcessao, 'read failed'):
                asr_ler_mem(parametros, processador, configuracao)

        self.assertEqual(processador.modos_de_reset_software, [0])

    def test_ler_mem_imprime_hexdump_progressivamente_por_linha(self):
        processador = ProcessadorSimulado(valores_de_registradores={
            endereco: 0x04030201 for endereco in range(0x20000000, 0x20000014, 4)
        })
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(address=0x20000000, size=20, baud=921600, output=None)
        saida_padrao = io.StringIO()

        with contextlib.redirect_stdout(saida_padrao):
            asr_ler_mem(parametros, processador, configuracao)

        linhas = saida_padrao.getvalue().splitlines()
        self.assertIn('20000000', linhas[2])
        self.assertIn('20000010', linhas[3])

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

    def test_apagar_eeprom_v8_usa_ultimo_kib_da_regiao_reservada(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_apagamento={EEPROM_ENDERECO_V8_ASR6601SE}
        )

        with contextlib.redirect_stdout(io.StringIO()):
            variante = asr_apagar_eeprom(processador, v8=True)

        self.assertEqual(variante, 'ASR6601CB')
        self.assertEqual(processador.chamadas_de_apagamento, [
            (EEPROM_ENDERECO_V8_ASR6601CB, EEPROM_SIZE_V8),
            (EEPROM_ENDERECO_V8_ASR6601SE, EEPROM_SIZE_V8),
        ])

    def test_identificar_mcu_reutiliza_teste_de_eeprom_do_flash_para_se(self):
        processador = ProcessadorSimulado()
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(baud=921600)

        saida_padrao = io.StringIO()
        with contextlib.redirect_stdout(saida_padrao):
            variante = asr_identificar_mcu(parametros, processador, configuracao)

        self.assertEqual(variante, 'ASR6601SE')
        self.assertIn('MCU identificado: ASR6601SE', saida_padrao.getvalue())
        self.assertNotIn('Aviso:', saida_padrao.getvalue())
        self.assertNotIn('Dispositivo identificado:', saida_padrao.getvalue())
        self.assertEqual(processador.chamadas_de_apagamento, [
            (EEPROM_ENDERECO_ASR6601CB, EEPROM_SIZE),
            (EEPROM_ENDERECO_ASR6601SE, EEPROM_SIZE),
        ])

    def test_identificar_mcu_reutiliza_teste_de_eeprom_do_flash_para_cb(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_apagamento={EEPROM_ENDERECO_ASR6601SE}
        )
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(baud=921600)

        saida_padrao = io.StringIO()
        with contextlib.redirect_stdout(saida_padrao):
            variante = asr_identificar_mcu(parametros, processador, configuracao)

        self.assertEqual(variante, 'ASR6601CB')
        self.assertIn('MCU identificado: ASR6601CB', saida_padrao.getvalue())
        self.assertNotIn('Aviso:', saida_padrao.getvalue())
        self.assertNotIn('Dispositivo identificado:', saida_padrao.getvalue())
        self.assertEqual(processador.chamadas_de_apagamento, [
            (EEPROM_ENDERECO_ASR6601CB, EEPROM_SIZE),
            (EEPROM_ENDERECO_ASR6601SE, EEPROM_SIZE),
        ])

    def test_mapa_memoria_mostra_faixas_do_cb(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_apagamento={EEPROM_ENDERECO_ASR6601SE}
        )
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(baud=921600)

        saida_padrao = io.StringIO()
        with contextlib.redirect_stdout(saida_padrao):
            mapa = asr_mapa_memoria(parametros, processador, configuracao)

        self.assertEqual(mapa, (
            ('Flash interna', 0x08000000, 0x08020000, 128 * 1024),
            ('SRAM', 0x20000000, 0x20004000, 16 * 1024),
            ('EEPROM emulada', EEPROM_ENDERECO_ASR6601CB,
             EEPROM_ENDERECO_ASR6601CB + EEPROM_SIZE, EEPROM_SIZE),
        ))
        self.assertIn('Flash interna: 0x08000000 - 0x0801FFFF (128 KiB)', saida_padrao.getvalue())
        self.assertIn('SRAM: 0x20000000 - 0x20003FFF (16 KiB)', saida_padrao.getvalue())
        self.assertIn('EEPROM emulada: 0x0801F000 - 0x0801FFFF (4 KiB)', saida_padrao.getvalue())

    def test_mapa_sram_mostra_apenas_faixa_do_se(self):
        processador = ProcessadorSimulado()
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        parametros = SimpleNamespace(baud=921600)

        with contextlib.redirect_stdout(io.StringIO()):
            mapa = asr_mapa_memoria(parametros, processador, configuracao, 'SRAM')

        self.assertEqual(mapa, (('SRAM', 0x20000000, 0x20010000, 64 * 1024),))

    def test_mapa_eeprom_v8_mostra_apenas_ultimo_kib(self):
        processador = ProcessadorSimulado(
            enderecos_com_falha_de_apagamento={EEPROM_ENDERECO_V8_ASR6601SE}
        )
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'], v8=True)
        parametros = SimpleNamespace(baud=921600)

        with contextlib.redirect_stdout(io.StringIO()):
            mapa = asr_mapa_memoria(parametros, processador, configuracao, 'EEPROM emulada')

        self.assertEqual(mapa, ((
                                    'EEPROM emulada', EEPROM_ENDERECO_V8_ASR6601CB,
                                    EEPROM_ENDERECO_V8_ASR6601CB + EEPROM_SIZE_V8, EEPROM_SIZE_V8,
                                ),))

    def test_mapa_eeprom_le_bytes_sem_apagar_quando_mcu_e_informado(self):
        enderecos = range(EEPROM_ENDERECO_ASR6601CB, EEPROM_ENDERECO_ASR6601CB + EEPROM_SIZE, 4)
        processador = ProcessadorSimulado(
            valores_de_registradores={endereco: 0x04030201 for endereco in enderecos}
        )
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])

        with tempfile.TemporaryDirectory() as diretorio_temporario:
            diretorio_original = os.getcwd()
            try:
                os.chdir(diretorio_temporario)
                parametros = SimpleNamespace(baud=921600, mcu='cb', output=None)
                with contextlib.redirect_stdout(io.StringIO()):
                    dados = asr_mapa_memoria(
                        parametros, processador, configuracao, 'EEPROM emulada', ler_bytes=True
                    )

                arquivo = Path('mapas_memoria') / 'mapa_eeprom.bin'
                self.assertTrue(arquivo.parent.is_dir())
                self.assertEqual(arquivo.read_bytes(), dados)
            finally:
                os.chdir(diretorio_original)

        self.assertEqual(dados, b'\x01\x02\x03\x04' * (EEPROM_SIZE // 4))
        self.assertEqual(processador.chamadas_de_apagamento, [])

    def test_mapa_eeprom_ab_le_as_duas_paginas_do_se_sem_apagar(self):
        enderecos = range(0x0803E000, 0x08040000, 4)
        processador = ProcessadorSimulado(valores_de_registradores={
            endereco: 0xAAAAAAAA if endereco < 0x0803F000 else 0xBBBBBBBB
            for endereco in enderecos
        })
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'], v8=True)
        with tempfile.TemporaryDirectory() as diretorio:
            arquivo = Path(diretorio) / 'mapa.bin'
            parametros = SimpleNamespace(baud=921600, mcu='se', eeprom_ab=True, output=arquivo)
            with contextlib.redirect_stdout(io.StringIO()):
                dados = asr_mapa_memoria(
                    parametros, processador, configuracao, 'EEPROM emulada', ler_bytes=True
                )
            self.assertEqual(arquivo.read_bytes(), dados)
        self.assertEqual(dados, b'\xAA' * 4096 + b'\xBB' * 4096)
        self.assertEqual(processador.leituras_de_registradores, list(enderecos))
        self.assertEqual(processador.chamadas_de_apagamento, [])

    def test_mapa_eeprom_ab_exige_se_antes_de_conectar(self):
        configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
        for mcu in (None, 'cb'):
            with self.subTest(mcu=mcu):
                processador = ProcessadorSimulado()
                parametros = SimpleNamespace(baud=921600, mcu=mcu, eeprom_ab=True)
                with self.assertRaisesRegex(CmdExcessao, '(?i)exige --mcu se'):
                    asr_mapa_memoria(parametros, processador, configuracao)
                self.assertEqual(processador.portas, [])
                self.assertEqual(processador.chamadas_de_apagamento, [])

    def test_mapa_eeprom_exporta_pagina_bruta_com_ou_sem_geracao(self):
        apagada = b'\xFF' * 4096
        bruto_a = b'A' + apagada[1:]
        bruto_b = b'B' + apagada[1:]
        cifrada = apagada[:-16] + struct.pack('<4I', 10, 10 ^ 0xFFFFFFFF, 549, 0x48444533)
        legada = bruto_b[:-16] + struct.pack('<4I', 11, 0, 11 ^ 0xFFFFFFFF, 0x48444532)
        incompleta = bruto_b[:-16] + struct.pack('<4I', 12, 0, 549, 0x48444533)

        for caso, primeira, segunda, indice, criterio in (
            ('legada mais nova', cifrada, legada, 1, 'geração 11'),
            ('maior geração na primeira', legada, cifrada, 0, 'geração 11'),
            ('mesma geração', cifrada, cifrada, 0, 'geração 10'),
            ('página cifrada sem autenticação', cifrada, apagada, 0, 'geração 10'),
            ('complemento inválido', cifrada, incompleta, 0, 'geração 10'),
            ('só primeira com dados', bruto_a, apagada, 0, 'sem geração identificável'),
            ('só segunda com dados', apagada, bruto_b, 1, 'sem geração identificável'),
            ('duas páginas sem cabeçalho', bruto_a, bruto_b, 1, 'sem geração identificável'),
            ('duas páginas apagadas', apagada, apagada, 1, 'sem geração identificável'),
        ):
            with self.subTest(caso=caso):
                bruto = primeira + segunda
                enderecos = range(0x0803E000, 0x08040000, 4)
                processador = ProcessadorSimulado(valores_de_registradores={
                    endereco: struct.unpack_from('<I', bruto, endereco - 0x0803E000)[0]
                    for endereco in enderecos
                })
                configuracao = SimpleNamespace(portas_disponiveis=['COM1'])
                with tempfile.TemporaryDirectory() as diretorio:
                    arquivo = Path(diretorio) / 'mapa.bin'
                    arquivo.write_bytes(b'dump anterior')
                    parametros = SimpleNamespace(baud=921600, mcu='se', eeprom_ativa=True, output=arquivo)
                    with contextlib.redirect_stdout(io.StringIO()) as console:
                        resultado = asr_mapa_memoria(parametros, processador, configuracao)
                    esperado = (primeira, segunda)[indice]
                    self.assertEqual(resultado, esperado)
                    self.assertEqual(arquivo.read_bytes(), esperado)
                    self.assertEqual(list(arquivo.parent.iterdir()), [arquivo])
                    endereco_escolhido = 0x0803E000 + 4096 * indice
                    self.assertIn(f'EEPROM 0x{endereco_escolhido:08X}', console.getvalue())
                    self.assertIn(criterio, console.getvalue())
                self.assertEqual(processador.leituras_de_registradores, list(enderecos))
                self.assertEqual(processador.chamadas_de_apagamento, [])
                self.assertEqual(processador.modos_de_reset_software, [0])

    @unittest.skipUnless(os.name == 'nt', 'Bloqueio de arquivo mapeado no Windows')
    def test_mapa_eeprom_preserva_dump_aberto_no_visualizador(self):
        anterior = b'A' * 4096
        pagina = b'B' * 4096
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / 'mapa_eeprom.bin'
            caminho.write_bytes(anterior)
            with caminho.open('rb') as arquivo, mmap.mmap(arquivo.fileno(), 0, access=mmap.ACCESS_READ) as visualizador:
                with contextlib.redirect_stdout(io.StringIO()) as console:
                    salvo = _salvar_mapa_eeprom(caminho, pagina)
                self.assertEqual(visualizador[:], anterior)
                self.assertIn('Arquivo anterior preservado', console.getvalue())
            self.assertNotEqual(salvo, caminho)
            self.assertEqual(salvo.parent, caminho.parent)
            self.assertEqual(salvo.read_bytes(), pagina)
            self.assertEqual(caminho.read_bytes(), anterior)

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
