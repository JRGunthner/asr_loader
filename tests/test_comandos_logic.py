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


class FakeCloseSerial:
    def __init__(self, fail_on_close=False):
        self.fail_on_close = fail_on_close
        self.closed = False

    def close(self):
        self.closed = True
        if self.fail_on_close:
            raise OSError('already gone')


class FakeProcessor:
    def __init__(self, fail_connect_ports=None, fail_erase_addrs=None, reg_values=None):
        self.ser = None
        self.current_port = None
        self.ports = []
        self.connected_ports = []
        self.baudrates = []
        self.dtr_states = []
        self.rts_states = []
        self.hw_reset_modes = []
        self.erase_calls = []
        self.reg_reads = []
        self.fail_connect_ports = set(fail_connect_ports or [])
        self.fail_erase_addrs = set(fail_erase_addrs or [])
        self.reg_values = dict(reg_values or {})

    def set_port(self, port, baud=None):
        self.current_port = port
        self.ports.append((port, baud))
        self.ser = FakeCloseSerial()

    def conectar(self):
        self.connected_ports.append(self.current_port)
        if self.current_port in self.fail_connect_ports:
            raise Exception('connect failed')

    def set_baudrate(self, baud):
        self.baudrates.append(baud)

    def erase(self, address, size):
        self.erase_calls.append((address, size))
        if address in self.fail_erase_addrs:
            raise Exception('erase failed')

    def ler_reg(self, address):
        self.reg_reads.append(address)
        return (self.reg_values[address],)

    def set_dtr(self, state):
        self.dtr_states.append(state)

    def set_rts(self, state):
        self.rts_states.append(state)

    def hw_reset(self, mode):
        self.hw_reset_modes.append(mode)


class ComandosLogicTests(unittest.TestCase):
    def test_asr_fechar_porta_closes_and_clears_serial(self):
        processador = SimpleNamespace(ser=FakeCloseSerial())

        asr_fechar_porta(processador)

        self.assertIsNone(processador.ser)

    def test_asr_fechar_porta_ignores_close_oserror(self):
        processador = SimpleNamespace(ser=FakeCloseSerial(fail_on_close=True))

        asr_fechar_porta(processador)

        self.assertIsNone(processador.ser)

    def test_asr_conectar_tries_ports_in_reverse_order_until_success(self):
        processador = FakeProcessor(fail_connect_ports={'COM2'})

        with contextlib.redirect_stdout(io.StringIO()):
            result = asr_conectar(processador, ['COM1', 'COM2'], 115200)

        self.assertTrue(result)
        self.assertEqual(processador.connected_ports, ['COM2', 'COM1'])
        self.assertEqual(processador.baudrates, [115200])

    def test_asr_conectar_raises_when_no_ports_are_available(self):
        with self.assertRaisesRegex(CmdExcessao, 'nenhuma porta serial'):
            asr_conectar(FakeProcessor(), [], 115200)

    def test_asr_conectar_raises_after_all_ports_fail(self):
        processador = FakeProcessor(fail_connect_ports={'COM1', 'COM2'})

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(CmdExcessao, 'nao foi possivel conectar'):
                asr_conectar(processador, ['COM1', 'COM2'], 115200)

        self.assertEqual(processador.connected_ports, ['COM2', 'COM1'])

    def test_hexdump_formats_address_hex_and_ascii(self):
        dump = asr_formatar_hexdump(0x20000000, b'ABC\x00\xff')

        self.assertIn('20000000', dump)
        self.assertIn('41 42 43 00 FF', dump)
        self.assertIn('|ABC..|', dump)

    def test_address_range_helpers_cover_boundaries(self):
        self.assertTrue(asr_endereco_em_faixa_app(0x08000000))
        self.assertTrue(asr_endereco_em_faixa_app(0x0803FFFF))
        self.assertFalse(asr_endereco_em_faixa_app(0x08040000))
        self.assertTrue(asr_endereco_em_sram(0x20000000))
        self.assertTrue(asr_endereco_em_sram(0x3FFFFFFF))
        self.assertFalse(asr_endereco_em_sram(0x40000000))

    def test_ler_mem_reads_aligned_words_and_returns_requested_slice(self):
        processador = FakeProcessor(reg_values={
            0x20000000: 0x04030201,
            0x20000004: 0x08070605,
        })
        config = SimpleNamespace(portas_disponiveis=['COM1'])
        param = SimpleNamespace(address=0x20000001, size=5, baud=921600, output=None)

        with contextlib.redirect_stdout(io.StringIO()):
            dados = asr_ler_mem(param, processador, config)

        self.assertEqual(dados, b'\x02\x03\x04\x05\x06')
        self.assertEqual(processador.reg_reads, [0x20000000, 0x20000004])

    def test_ler_mem_can_write_raw_dump_to_file(self):
        processador = FakeProcessor(reg_values={0x20000000: 0x04030201})
        config = SimpleNamespace(portas_disponiveis=['COM1'])

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / 'dump.bin'
            param = SimpleNamespace(address=0x20000000, size=4, baud=921600, output=str(output))
            with contextlib.redirect_stdout(io.StringIO()):
                dados = asr_ler_mem(param, processador, config)
            self.assertEqual(output.read_bytes(), dados)

        self.assertEqual(dados, b'\x01\x02\x03\x04')

    def test_ler_mem_rejects_non_positive_size_before_connecting(self):
        processador = FakeProcessor()
        config = SimpleNamespace(portas_disponiveis=['COM1'])
        param = SimpleNamespace(address=0x20000000, size=0, baud=921600, output=None)

        with self.assertRaisesRegex(Exception, 'tamanho'):
            asr_ler_mem(param, processador, config)

        self.assertEqual(processador.ports, [])

    def test_apagar_eeprom_detects_successful_variant(self):
        processador = FakeProcessor(fail_erase_addrs={EEPROM_ENDERECO_ASR6601CB})

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            asr_apagar_eeprom(processador)

        self.assertEqual(processador.erase_calls, [
            (EEPROM_ENDERECO_ASR6601CB, EEPROM_SIZE),
            (EEPROM_ENDERECO_ASR6601SE, EEPROM_SIZE),
        ])
        self.assertIn('ASR6601SE', stdout.getvalue())

    def test_apagar_eeprom_raises_when_all_mappings_fail(self):
        processador = FakeProcessor(fail_erase_addrs={EEPROM_ENDERECO_ASR6601CB, EEPROM_ENDERECO_ASR6601SE})

        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(Exception, 'todos os mapeamentos'):
                asr_apagar_eeprom(processador)

    def test_controlar_linha_serial_sets_dtr_and_closes_port(self):
        processador = FakeProcessor()
        config = SimpleNamespace(portas_disponiveis=['COM3'])
        param = SimpleNamespace(baud=57600, control_line='dtr', control_state=True, hold=0)

        with contextlib.redirect_stdout(io.StringIO()):
            result = asr_controlar_linha_serial(param, processador, config)

        self.assertTrue(result)
        self.assertEqual(processador.ports, [('COM3', 57600)])
        self.assertEqual(processador.dtr_states, [True])
        self.assertEqual(processador.rts_states, [])
        self.assertIsNone(processador.ser)

    def test_controlar_linha_serial_rejects_negative_hold(self):
        processador = FakeProcessor()
        config = SimpleNamespace(portas_disponiveis=['COM3'])
        param = SimpleNamespace(baud=57600, control_line='dtr', control_state=True, hold=-1)

        with self.assertRaisesRegex(Exception, '--hold'):
            asr_controlar_linha_serial(param, processador, config)

        self.assertEqual(processador.ports, [])

    def test_hw_reset_uses_selected_port_and_closes_after_pulse(self):
        processador = FakeProcessor()
        config = SimpleNamespace(portas_disponiveis=['COM4'])
        param = SimpleNamespace(baud=115200, boot=True)

        with contextlib.redirect_stdout(io.StringIO()):
            result = asr_hw_reset(param, processador, config)

        self.assertTrue(result)
        self.assertEqual(processador.ports, [('COM4', 115200)])
        self.assertEqual(processador.hw_reset_modes, [1])
        self.assertIsNone(processador.ser)


if __name__ == '__main__':
    unittest.main()
