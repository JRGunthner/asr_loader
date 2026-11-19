import contextlib
import io
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.comandos import asr_ota_pack, asr_ota_pack_ler_info
from src.ota_comum import (
    append_ota_tche_sufixo,
    parse_key_from_header,
    split_ota_tche_sufixo,
)
from src.ota_pacote_cripto import (
    aplicar_siphash64_ctr_xor,
    caminho_saida_segura_padrao,
    montar_pacote_seguro,
    verificar_pacote_seguro,
)


class TestesDosPacotesOta(unittest.TestCase):
    def test_comando_ota_pack_monta_pacote_simples_valido(self):
        firmware = bytes(range(64))

        with tempfile.TemporaryDirectory() as diretorio_temporario:
            caminho_firmware = Path(diretorio_temporario) / 'app.bin'
            caminho_saida = Path(diretorio_temporario) / 'app_ota.bin'
            caminho_firmware.write_bytes(firmware)

            argumentos = SimpleNamespace(
                firmware=str(caminho_firmware), output=str(caminho_saida)
            )
            with contextlib.redirect_stdout(io.StringIO()):
                asr_ota_pack(argumentos)

            informacoes = asr_ota_pack_ler_info(str(caminho_saida))
            self.assertEqual(informacoes['firmware'], firmware)
            self.assertEqual(informacoes['fw_size'], len(firmware))
            self.assertEqual(informacoes['reservado'], 0)

    def test_analisar_chave_do_cabecalho_aceita_decimal_multilinha_e_sufixos_c(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            cabecalho = Path(diretorio_temporario) / 'boot_security_config.h'
            cabecalho.write_text(
                '#define BOOT_SECURITY_KEY_BYTES { \\\n'
                '    0x00U, 1, 0x02UL, 3U, \\\n'
                '    4, 5, 6, 7, \\\n'
                '    8, 9, 10, 11, \\\n'
                '    12, 13, 14, 15 \\\n'
                '}\n',
                encoding='utf-8',
            )

            chave = parse_key_from_header(cabecalho)

        self.assertEqual(chave, bytes(range(16)))

    def test_analisar_chave_do_cabecalho_rejeita_quantidade_incorreta_de_bytes(self):
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            cabecalho = Path(diretorio_temporario) / 'boot_security_config.h'
            cabecalho.write_text(
                '#define BOOT_SECURITY_KEY_BYTES { 0x00, 0x01 }\n',
                encoding='utf-8',
            )

            with self.assertRaisesRegex(ValueError, 'Esperados 16 bytes'):
                parse_key_from_header(cabecalho)

    def test_separar_sufixo_ota_tche_aceita_pacotes_simples_e_com_sufixo(self):
        pacote = b'abc'

        self.assertEqual(split_ota_tche_sufixo(pacote, 3), pacote)
        self.assertEqual(
            split_ota_tche_sufixo(append_ota_tche_sufixo(pacote), 3), pacote
        )

        with self.assertRaisesRegex(ValueError, 'Tamanho total invalido'):
            split_ota_tche_sufixo(pacote + b'x', 3)

    def test_pacote_criptografado_completa_ciclo_de_ida_e_volta(self):
        firmware = b'firmware de teste criptografado'
        chave = bytes(range(16))
        nonce = b'12345678'

        pacote = montar_pacote_seguro(
            firmware, versao_firmware=9, chave=chave, nonce=nonce
        )
        pacote_analisado, texto_simples = verificar_pacote_seguro(pacote, chave)

        self.assertEqual(texto_simples, firmware)
        self.assertEqual(pacote_analisado.versao_firmware, 9)
        self.assertEqual(pacote_analisado.nonce, nonce)

    def test_pacote_criptografado_rejeita_tamanho_invalido_de_nonce(self):
        with self.assertRaisesRegex(ValueError, 'nonce'):
            montar_pacote_seguro(b'fw', versao_firmware=1, chave=bytes(range(16)), nonce=b'curto')

    def test_pacote_criptografado_rejeita_texto_cifrado_adulterado(self):
        firmware = b'firmware de teste criptografado'
        chave = bytes(range(16))
        pacote = bytearray(
            montar_pacote_seguro(
                firmware, versao_firmware=9, chave=chave, nonce=b'12345678'
            )
        )
        pacote[16] ^= 0x01

        with self.assertRaisesRegex(ValueError, 'auth_tag'):
            verificar_pacote_seguro(bytes(pacote), chave)

    def test_verificacao_segura_rejeita_trailer_de_versao_1(self):
        firmware = bytes(range(64))
        chave = bytes(range(16))
        pacote = bytearray(montar_pacote_seguro(firmware, versao_firmware=3, chave=chave))
        struct.pack_into('<I', pacote, 16 + len(firmware) + 4, 1)

        with self.assertRaisesRegex(ValueError, 'Versao de trailer nao suportada: 1'):
            verificar_pacote_seguro(bytes(pacote), chave)

    def test_siphash_ctr_xor_e_reversivel(self):
        firmware = b'payload claro'
        chave = bytes(range(16))
        nonce = b'12345678'

        texto_cifrado = aplicar_siphash64_ctr_xor(firmware, chave, nonce)
        texto_simples = aplicar_siphash64_ctr_xor(texto_cifrado, chave, nonce)

        self.assertNotEqual(texto_cifrado, firmware)
        self.assertEqual(texto_simples, firmware)

    def test_caminho_padrao_de_saida_segura_preserva_sufixo_ou_usa_bin(self):
        self.assertEqual(caminho_saida_segura_padrao(Path('app')), Path('app_ota_cript.bin'))
        self.assertEqual(caminho_saida_segura_padrao(Path('app.hex')), Path('app_ota_cript.hex'))


if __name__ == '__main__':
    unittest.main()
