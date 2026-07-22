import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.comandos import asr_ota_pack, asr_ota_pack_ler_info
from src.ota_assinado import (
    append_ota_tche_sufixo,
    build_ota_assinado_package,
    ota_assinado_verify_package,
    parse_key_from_header,
    split_ota_tche_sufixo,
)
from src.ota_pacote_cripto import (
    aplicar_siphash64_ctr_xor,
    caminho_saida_segura_padrao,
    montar_pacote_seguro,
    verificar_pacote_seguro,
)


class OtaPackageTests(unittest.TestCase):
    def test_ota_pack_command_builds_valid_simple_package(self):
        firmware = bytes(range(64))

        with tempfile.TemporaryDirectory() as temp_dir:
            firmware_path = Path(temp_dir) / 'app.bin'
            output_path = Path(temp_dir) / 'app_ota.bin'
            firmware_path.write_bytes(firmware)

            args = SimpleNamespace(firmware=str(firmware_path), output=str(output_path))
            with contextlib.redirect_stdout(io.StringIO()):
                asr_ota_pack(args)

            info = asr_ota_pack_ler_info(str(output_path))
            self.assertEqual(info['firmware'], firmware)
            self.assertEqual(info['fw_size'], len(firmware))
            self.assertEqual(info['reservado'], 0)

    def test_signed_package_roundtrip(self):
        firmware = b'firmware de teste assinado'
        key = bytes(range(16))

        package = build_ota_assinado_package(firmware, firmware_version=7, key=key)
        size, version, auth_tag = ota_assinado_verify_package(package, key)

        self.assertEqual(size, len(firmware))
        self.assertEqual(version, 7)
        self.assertEqual(len(auth_tag), 16)

    def test_signed_package_rejects_tampered_payload(self):
        firmware = b'firmware de teste assinado'
        key = bytes(range(16))
        package = bytearray(build_ota_assinado_package(firmware, firmware_version=7, key=key))
        package[20] ^= 0x01

        with self.assertRaises(ValueError):
            ota_assinado_verify_package(bytes(package), key)

    def test_parse_key_from_header_accepts_multiline_decimal_and_c_suffixes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            header = Path(temp_dir) / 'boot_security_config.h'
            header.write_text(
                '#define BOOT_SECURITY_KEY_BYTES { \\\n'
                '    0x00U, 1, 0x02UL, 3U, \\\n'
                '    4, 5, 6, 7, \\\n'
                '    8, 9, 10, 11, \\\n'
                '    12, 13, 14, 15 \\\n'
                '}\n',
                encoding='utf-8',
            )

            key = parse_key_from_header(header)

        self.assertEqual(key, bytes(range(16)))

    def test_parse_key_from_header_rejects_wrong_number_of_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            header = Path(temp_dir) / 'boot_security_config.h'
            header.write_text('#define BOOT_SECURITY_KEY_BYTES { 0x00, 0x01 }\n', encoding='utf-8')

            with self.assertRaisesRegex(ValueError, 'Esperados 16 bytes'):
                parse_key_from_header(header)

    def test_split_ota_tche_suffix_accepts_plain_and_suffixed_packages(self):
        package = b'abc'

        self.assertEqual(split_ota_tche_sufixo(package, 3), package)
        self.assertEqual(split_ota_tche_sufixo(append_ota_tche_sufixo(package), 3), package)

        with self.assertRaisesRegex(ValueError, 'Tamanho total invalido'):
            split_ota_tche_sufixo(package + b'x', 3)

    def test_encrypted_package_roundtrip(self):
        firmware = b'firmware de teste criptografado'
        key = bytes(range(16))
        nonce = b'12345678'

        package = montar_pacote_seguro(firmware, versao_firmware=9, chave=key, nonce=nonce)
        parsed, plaintext = verificar_pacote_seguro(package, key)

        self.assertEqual(plaintext, firmware)
        self.assertEqual(parsed.versao_firmware, 9)
        self.assertEqual(parsed.nonce, nonce)

    def test_encrypted_package_rejects_invalid_nonce_size(self):
        with self.assertRaisesRegex(ValueError, 'nonce'):
            montar_pacote_seguro(b'fw', versao_firmware=1, chave=bytes(range(16)), nonce=b'curto')

    def test_encrypted_package_rejects_tampered_ciphertext(self):
        firmware = b'firmware de teste criptografado'
        key = bytes(range(16))
        package = bytearray(montar_pacote_seguro(firmware, versao_firmware=9, chave=key, nonce=b'12345678'))
        package[16] ^= 0x01

        with self.assertRaisesRegex(ValueError, 'auth_tag'):
            verificar_pacote_seguro(bytes(package), key)

    def test_secure_verify_accepts_legacy_signed_package(self):
        firmware = b'legacy assinado'
        key = bytes(range(16))
        package = build_ota_assinado_package(firmware, firmware_version=3, key=key)

        parsed, plaintext = verificar_pacote_seguro(package, key)

        self.assertEqual(plaintext, firmware)
        self.assertEqual(parsed.versao_trailer, 1)

    def test_siphash_ctr_xor_is_reversible(self):
        firmware = b'payload claro'
        key = bytes(range(16))
        nonce = b'12345678'

        ciphertext = aplicar_siphash64_ctr_xor(firmware, key, nonce)
        plaintext = aplicar_siphash64_ctr_xor(ciphertext, key, nonce)

        self.assertNotEqual(ciphertext, firmware)
        self.assertEqual(plaintext, firmware)

    def test_default_secure_output_path_preserves_suffix_or_uses_bin(self):
        self.assertEqual(caminho_saida_segura_padrao(Path('app')), Path('app_ota_cript.bin'))
        self.assertEqual(caminho_saida_segura_padrao(Path('app.hex')), Path('app_ota_cript.hex'))


if __name__ == '__main__':
    unittest.main()
