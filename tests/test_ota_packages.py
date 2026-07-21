import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.comandos import asr_ota_pack, asr_ota_pack_ler_info
from src.ota_assinado import build_ota_assinado_package, ota_assinado_verify_package
from src.ota_pacote_cripto import montar_pacote_seguro, verificar_pacote_seguro


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

    def test_encrypted_package_roundtrip(self):
        firmware = b'firmware de teste criptografado'
        key = bytes(range(16))
        nonce = b'12345678'

        package = montar_pacote_seguro(firmware, versao_firmware=9, chave=key, nonce=nonce)
        parsed, plaintext = verificar_pacote_seguro(package, key)

        self.assertEqual(plaintext, firmware)
        self.assertEqual(parsed.versao_firmware, 9)
        self.assertEqual(parsed.nonce, nonce)


if __name__ == '__main__':
    unittest.main()
