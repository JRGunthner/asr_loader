import contextlib
import io
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ASRLoader import ASRLoader
from src.constantes import (
    CMD_BAUDRATE,
    CMD_ERASE,
    CMD_FLASH,
    CMD_JUMP,
    CMD_RDOTP,
    CMD_RDOPT0,
    CMD_RDOPT1,
    CMD_RDREG,
    CMD_REBOOT,
    CMD_SN,
    CMD_SYNC,
    CMD_VERIFY,
    CMD_VERSION,
    CMD_WROPT0,
    CMD_WROPT1,
    CMD_WROTP,
    CMD_WRREG,
)
from src.exceptions import CmdExcessao


class ConfiguracaoSimulada:
    def __init__(self):
        self.verbose = False
        self.com_timeout = 2
        self.auto_boot = True
        self.boot_reset_delay = 0.1
        self.boot_release_delay = 0.2
        self.logs = []

    def log(self, mensagem):
        self.logs.append(mensagem)


class SerialSimulada:
    def __init__(self, blocos_de_leitura=None):
        self.port = 'COM_TEST'
        self.baudrate = 9600
        self.read_chunks = list(blocos_de_leitura or [])
        self.writes = []
        self.dtr_states = []
        self.rts_states = []
        self.flush_input_count = 0
        self.flush_output_count = 0
        self.closed = False

    def read(self, _tamanho):
        if not self.read_chunks:
            return b''
        return self.read_chunks.pop(0)

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def close(self):
        self.closed = True

    def set_dtr(self, state):
        self.dtr_states.append(state)

    def set_rts(self, state):
        self.rts_states.append(state)

    def flush_input(self):
        self.flush_input_count += 1

    def flush_output(self):
        self.flush_output_count += 1


def montar_pacote_de_resposta(status=0, dados=b''):
    cabecalho = struct.pack('<BBH', 0xFE, status, len(dados))
    crc = zlib.crc32(cabecalho + dados) & 0xFFFFFFFF
    return cabecalho + dados + struct.pack('<IB', crc, 0xEF)


def criar_carregador(serial_simulada=None):
    configuracao = ConfiguracaoSimulada()
    carregador = ASRLoader(configuracao)
    carregador.ser = serial_simulada or SerialSimulada()
    return carregador, configuracao


class TestesDoProtocoloASRLoader(unittest.TestCase):
    def obter_comando_escrito(self, serial_simulada, indice=0):
        pacote = serial_simulada.writes[indice]
        inicio, comando, tamanho_dados = struct.unpack('<BBH', pacote[:4])
        self.assertEqual(inicio, 0xFE)
        return comando, pacote[4:4 + tamanho_dados]

    def test_enviar_cmd_monta_pacote_com_crc_e_marcador_final(self):
        serial_simulada = SerialSimulada()
        carregador, configuracao = criar_carregador(serial_simulada)

        carregador.enviar_cmd(CMD_SYNC, b'ab')

        self.assertEqual(serial_simulada.flush_input_count, 1)
        self.assertEqual(len(serial_simulada.writes), 1)
        pacote = serial_simulada.writes[0]
        self.assertEqual(pacote[:4], struct.pack('<BBH', 0xFE, CMD_SYNC, 2))
        self.assertEqual(pacote[4:6], b'ab')
        self.assertEqual(pacote[-1], 0xEF)
        crc_esperado = zlib.crc32(pacote[:-5]) & 0xFFFFFFFF
        crc_atual = struct.unpack('<I', pacote[-5:-1])[0]
        self.assertEqual(crc_atual, crc_esperado)
        self.assertTrue(any('Tx' in item for item in configuracao.logs))

    def test_aguardar_resposta_retorna_status_e_dados(self):
        pacote = montar_pacote_de_resposta(status=0, dados=b'\x01\x02\x03')
        serial_simulada = SerialSimulada([pacote[:4], pacote[4:]])
        carregador, configuracao = criar_carregador(serial_simulada)

        status, dados = carregador.aguardar_resposta()

        self.assertEqual(status, 0)
        self.assertEqual(dados, b'\x01\x02\x03')
        self.assertTrue(any('Rx' in item for item in configuracao.logs))

    def test_aguardar_resposta_rejeita_marcador_inicial_invalido(self):
        header = struct.pack('<BBH', 0x00, 0, 0)
        serial_simulada = SerialSimulada([header])
        carregador, _configuracao = criar_carregador(serial_simulada)

        with self.assertRaisesRegex(CmdExcessao, 'pacote de resposta errado'):
            carregador.aguardar_resposta()

    def test_aguardar_resposta_rejeita_crc_invalido(self):
        packet = bytearray(montar_pacote_de_resposta(status=0, dados=b'x'))
        packet[-5] ^= 0xFF
        fake = SerialSimulada([bytes(packet[:4]), bytes(packet[4:])])
        loader, _config = criar_carregador(fake)

        with self.assertRaisesRegex(CmdExcessao, 'CRC errado'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_rejeita_marcador_final_invalido(self):
        packet = bytearray(montar_pacote_de_resposta(status=0, dados=b'x'))
        packet[-1] = 0
        fake = SerialSimulada([bytes(packet[:4]), bytes(packet[4:])])
        loader, _config = criar_carregador(fake)

        with self.assertRaisesRegex(CmdExcessao, 'pacote de resposta errado'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_rejeita_dados_acima_do_limite(self):
        fake = SerialSimulada([struct.pack('<BBH', 0xFE, 0, 513)])
        loader, _config = criar_carregador(fake)

        with self.assertRaisesRegex(CmdExcessao, 'tamanho do pacote'):
            loader.aguardar_resposta()

    def test_aguardar_resposta_expira_com_cabecalho_vazio(self):
        fake = SerialSimulada([b''])
        loader, config = criar_carregador(fake)

        with self.assertRaisesRegex(CmdExcessao, 'timeout leitura do header'):
            loader.aguardar_resposta()
        self.assertIn('Rx timeout header', config.logs)

    def test_aguardar_resposta_expira_com_dados_vazios(self):
        fake = SerialSimulada([struct.pack('<BBH', 0xFE, 0, 1), b''])
        loader, config = criar_carregador(fake)

        with self.assertRaisesRegex(CmdExcessao, 'timeout leitura de dados'):
            loader.aguardar_resposta()
        self.assertIn('Rx timeout dados', config.logs)

    def test_comandos_de_escrita_enviam_dados_esperados(self):
        cases = [
            (
                'jump',
                lambda ldr: ldr.jump(0x08000123),
                CMD_JUMP,
                struct.pack('<I', 0x08000123),
            ),
            (
                'flash',
                lambda ldr: ldr.flash(0x08000000, b'abcd'),
                CMD_FLASH,
                struct.pack('<II', 0x08000000, 4) + b'abcd',
            ),
            (
                'erase',
                lambda ldr: ldr.erase(0x08000000, 4096),
                CMD_ERASE,
                struct.pack('<II', 0x08000000, 4096),
            ),
            (
                'verify',
                lambda ldr: ldr.verify(0x08000000, 128, 0x12345678),
                CMD_VERIFY,
                struct.pack('<III', 0x08000000, 128, 0x12345678),
            ),
            (
                'escrever_otp',
                lambda ldr: ldr.escrever_otp(0x1FFF7000, b'\xAA\x55'),
                CMD_WROTP,
                struct.pack('<II', 0x1FFF7000, 2) + b'\xAA\x55',
            ),
            (
                'escrever_opt0',
                lambda ldr: ldr.escrever_opt0(0x11223344, 0x55667788),
                CMD_WROPT0,
                struct.pack('<II', 0x11223344, 0x55667788),
            ),
            (
                'escrever_opt1',
                lambda ldr: ldr.escrever_opt1(0x99AABBCC, 0xDDEEFF00),
                CMD_WROPT1,
                struct.pack('<II', 0x99AABBCC, 0xDDEEFF00),
            ),
            (
                'sw_reset',
                lambda ldr: ldr.sw_reset(1),
                CMD_REBOOT,
                struct.pack('B', 1),
            ),
            (
                'escrever_reg',
                lambda ldr: ldr.escrever_reg(0x40021000, 0x1234),
                CMD_WRREG,
                struct.pack('<II', 0x40021000, 0x1234),
            ),
        ]

        for name, action, expected_command, expected_payload in cases:
            with self.subTest(name=name):
                packet = montar_pacote_de_resposta(status=0)
                fake = SerialSimulada([packet[:4], packet[4:]])
                loader, _config = criar_carregador(fake)

                action(loader)

                command, payload = self.obter_comando_escrito(fake)
                self.assertEqual(command, expected_command)
                self.assertEqual(payload, expected_payload)

    def test_comandos_de_leitura_retornam_dados_decodificados(self):
        cases = [
            (
                'ler_otp',
                lambda ldr: ldr.ler_otp(0x1FFF7000, 4),
                CMD_RDOTP,
                struct.pack('<II', 0x1FFF7000, 4),
                b'abcd',
                b'abcd',
            ),
            (
                'ler_opt0',
                lambda ldr: ldr.ler_opt0(),
                CMD_RDOPT0,
                b'',
                struct.pack('<II', 0x11223344, 0x55667788),
                (0x11223344, 0x55667788),
            ),
            (
                'ler_opt1',
                lambda ldr: ldr.ler_opt1(),
                CMD_RDOPT1,
                b'',
                struct.pack('<II', 0x99AABBCC, 0xDDEEFF00),
                (0x99AABBCC, 0xDDEEFF00),
            ),
            (
                'ler_reg',
                lambda ldr: ldr.ler_reg(0x40021000),
                CMD_RDREG,
                struct.pack('<I', 0x40021000),
                struct.pack('<I', 0x12345678),
                (0x12345678,),
            ),
            (
                'versao_bootloader',
                lambda ldr: ldr.versao_bootloader(),
                CMD_VERSION,
                b'',
                struct.pack('<I', 0x01020304),
                (0x01020304,),
            ),
        ]

        for name, action, expected_command, expected_payload, response_payload, expected_result in cases:
            with self.subTest(name=name):
                packet = montar_pacote_de_resposta(status=0, dados=response_payload)
                fake = SerialSimulada([packet[:4], packet[4:]])
                loader, _config = criar_carregador(fake)

                result = action(loader)

                command, payload = self.obter_comando_escrito(fake)
                self.assertEqual(command, expected_command)
                self.assertEqual(payload, expected_payload)
                self.assertEqual(result, expected_result)

    def test_metodos_de_comando_lancam_excecao_com_status_diferente_de_zero(self):
        cases = [
            ('jump', lambda ldr: ldr.jump(0x08000123)),
            ('flash', lambda ldr: ldr.flash(0x08000000, b'abcd')),
            ('erase', lambda ldr: ldr.erase(0x08000000, 4096)),
            ('verify', lambda ldr: ldr.verify(0x08000000, 128, 0x12345678)),
            ('escrever_otp', lambda ldr: ldr.escrever_otp(0x1FFF7000, b'\xAA')),
            ('ler_otp', lambda ldr: ldr.ler_otp(0x1FFF7000, 4)),
            ('escrever_opt0', lambda ldr: ldr.escrever_opt0(1, 2)),
            ('ler_opt0', lambda ldr: ldr.ler_opt0()),
            ('escrever_opt1', lambda ldr: ldr.escrever_opt1(1, 2)),
            ('ler_opt1', lambda ldr: ldr.ler_opt1()),
            ('sw_reset', lambda ldr: ldr.sw_reset()),
            ('serial_asr', lambda ldr: ldr.serial_asr()),
            ('escrever_reg', lambda ldr: ldr.escrever_reg(0x40021000, 1)),
            ('ler_reg', lambda ldr: ldr.ler_reg(0x40021000)),
            ('versao_bootloader', lambda ldr: ldr.versao_bootloader()),
        ]

        for name, action in cases:
            with self.subTest(name=name):
                packet = montar_pacote_de_resposta(status=1)
                fake = SerialSimulada([packet[:4], packet[4:]])
                loader, _config = criar_carregador(fake)

                with self.assertRaises(CmdExcessao):
                    action(loader)

    def test_serial_asr_retorna_dados_quando_status_e_valido(self):
        packet = montar_pacote_de_resposta(status=0, dados=b'1234567890abcdef')
        fake = SerialSimulada([packet[:4], packet[4:]])
        loader, _config = criar_carregador(fake)

        serial = loader.serial_asr()

        self.assertEqual(serial, b'1234567890abcdef')
        command, payload = self.obter_comando_escrito(fake)
        self.assertEqual(command, CMD_SN)
        self.assertEqual(payload, b'')

    def test_definir_baudrate_envia_comando_e_atualiza_baudrate_serial(self):
        packet = montar_pacote_de_resposta(status=0)
        fake = SerialSimulada([packet[:4], packet[4:]])
        loader, config = criar_carregador(fake)

        loader.set_baudrate(115200)

        self.assertEqual(fake.baudrate, 115200)
        command, payload = self.obter_comando_escrito(fake)
        self.assertEqual(command, CMD_BAUDRATE)
        self.assertEqual(payload, struct.pack('<I', 115200))
        self.assertTrue(any('set_baudrate aplicado' in item for item in config.logs))

    def test_definir_porta_usa_adaptador_serial_e_tempo_limite_configurado(self):
        config = ConfiguracaoSimulada()
        loader = ASRLoader(config)
        fake = SerialSimulada()

        with mock.patch('src.ASRLoader.SerialPort', return_value=fake) as serial_port:
            loader.set_port('COM9', 57600)

        serial_port.assert_called_once_with('COM9', 57600, timeout=config.com_timeout)
        self.assertIs(loader.ser, fake)
        self.assertTrue(any('porta aberta' in item for item in config.logs))

    def test_sequencia_de_boot_por_reset_define_dtr_e_rts_em_ordem(self):
        fake = SerialSimulada()
        loader, _config = criar_carregador(fake)

        with mock.patch('src.ASRLoader.time.sleep') as sleep_mock:
            loader.hw_reset(1)

        self.assertEqual(fake.dtr_states, [False, True, False])
        self.assertEqual(fake.rts_states, [False, True, False])
        sleep_mock.assert_has_calls([mock.call(0.1), mock.call(0.2)])

    def test_reset_de_hardware_normal_libera_boot_e_pulsa_rts(self):
        fake = SerialSimulada()
        loader, _config = criar_carregador(fake)

        with mock.patch('src.ASRLoader.time.sleep') as sleep_mock:
            loader.hw_reset(0)

        self.assertEqual(fake.dtr_states, [False])
        self.assertEqual(fake.rts_states, [False, True, False])
        sleep_mock.assert_called_once_with(0.1)

    def test_conectar_sem_boot_automatico_apenas_sincroniza(self):
        packet = montar_pacote_de_resposta(status=0)
        fake = SerialSimulada([packet[:4], packet[4:]])
        loader, config = criar_carregador(fake)
        config.auto_boot = False

        with contextlib.redirect_stdout(io.StringIO()):
            loader.conectar(retentativas=1)

        self.assertEqual(fake.dtr_states, [])
        self.assertEqual(fake.rts_states, [])
        self.assertEqual(fake.flush_output_count, 1)
        self.assertEqual(fake.writes[0][1], CMD_SYNC)

    def test_conectar_tenta_novamente_e_fecha_serial_quando_sincronizacao_falha(self):
        fake = SerialSimulada([b'', b''])
        loader, config = criar_carregador(fake)
        config.auto_boot = False

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(CmdExcessao, 'Erro de conexao'):
                loader.conectar(retentativas=2)

        self.assertTrue(fake.closed)
        self.assertEqual(len(fake.writes), 2)
        self.assertTrue(any('falha_conexao' in item for item in config.logs))


if __name__ == '__main__':
    unittest.main()
