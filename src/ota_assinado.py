import binascii
import pathlib
import re
import struct
from typing import Tuple

OTA_MAGIC = 0xB00710AD
OTA_HEADER_SIZE = 16
OTA_AUTH_TRAILER_MAGIC = 0x41545548
OTA_AUTH_TRAILER_VERSION = 1
OTA_AUTH_FLAG_SIPHASH128 = 0x00000001
OTA_AUTH_TAG_SIZE = 16
TRAILER_STRUCT = struct.Struct("<IIII16sI")
HEADER_STRUCT = struct.Struct("<IIII")
PREFIX_STRUCT = struct.Struct("<IIIII")


def crc32_ieee(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def rotl64(value: int, bits: int) -> int:
    return ((value << bits) | (value >> (64 - bits))) & 0xFFFFFFFFFFFFFFFF


def sipround(v0: int, v1: int, v2: int, v3: int) -> Tuple[int, int, int, int]:
    v0 = (v0 + v1) & 0xFFFFFFFFFFFFFFFF
    v1 = rotl64(v1, 13)
    v1 ^= v0
    v0 = rotl64(v0, 32)
    v2 = (v2 + v3) & 0xFFFFFFFFFFFFFFFF
    v3 = rotl64(v3, 16)
    v3 ^= v2
    v0 = (v0 + v3) & 0xFFFFFFFFFFFFFFFF
    v3 = rotl64(v3, 21)
    v3 ^= v0
    v2 = (v2 + v1) & 0xFFFFFFFFFFFFFFFF
    v1 = rotl64(v1, 17)
    v1 ^= v2
    v2 = rotl64(v2, 32)
    return v0, v1, v2, v3


def siphash64(data: bytes, key: bytes, domain: int) -> int:
    if len(key) != 16:
        raise ValueError("A chave SipHash precisa ter 16 bytes")

    k0, k1 = struct.unpack("<QQ", key)
    v0 = 0x736F6D6570736575 ^ k0
    v1 = 0x646F72616E646F6D ^ k1
    v2 = 0x6C7967656E657261 ^ k0
    v3 = 0x7465646279746573 ^ k1

    v3 ^= domain & 0xFF
    v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
    v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
    v0 ^= domain & 0xFF

    offset = 0
    while offset + 8 <= len(data):
        (m,) = struct.unpack_from("<Q", data, offset)
        v3 ^= m
        v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
        v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
        v0 ^= m
        offset += 8

    tail = data[offset:]
    b = ((len(data) & 0xFF) << 56)
    for index, value in enumerate(tail):
        b |= value << (8 * index)

    v3 ^= b
    v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
    v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
    v0 ^= b
    v2 ^= 0xFF
    for _ in range(4):
        v0, v1, v2, v3 = sipround(v0, v1, v2, v3)

    return (v0 ^ v1 ^ v2 ^ v3) & 0xFFFFFFFFFFFFFFFF


def siphash128(data: bytes, key: bytes) -> bytes:
    lo = siphash64(data, key, 0)
    hi = siphash64(data, key, 1)
    return struct.pack("<QQ", lo, hi)


def parse_key_from_header(header_path: pathlib.Path) -> bytes:
    if not header_path.is_file():
        raise ValueError('Arquivo de chave nao encontrado: %s' % header_path)

    content = header_path.read_text(encoding="utf-8")
    match = re.search(r"#define\s+BOOT_SECURITY_KEY_BYTES\s+(.+)", content, re.MULTILINE)
    if not match:
        raise ValueError("Nao foi possivel localizar BOOT_SECURITY_KEY_BYTES")

    macro_value = match.group(1)
    while macro_value.rstrip().endswith("\\"):
        macro_value = macro_value.rstrip()[:-1]
        next_line_match = re.search(r"#define\s+BOOT_SECURITY_KEY_BYTES\s+.+\n((?:.+\n)+?)\n#ifdef", content, re.MULTILINE)
        if next_line_match:
            macro_value = (match.group(1) + "\n" + next_line_match.group(1)).replace("\\", " ")
        break

    values = re.findall(r"0x([0-9A-Fa-f]{1,2})U?", macro_value)
    if len(values) != 16:
        raise ValueError("Esperados 16 bytes de chave, encontrados %d" % len(values))

    return bytes(int(value, 16) for value in values)


def prefix_autenticado(firmware_version: int, firmware_size: int, firmware_crc32: int) -> bytes:
    return PREFIX_STRUCT.pack(
        OTA_AUTH_TRAILER_VERSION,
        OTA_AUTH_FLAG_SIPHASH128,
        firmware_version & 0xFFFFFFFF,
        firmware_size & 0xFFFFFFFF,
        firmware_crc32 & 0xFFFFFFFF,
    )


def build_ota_assinado_package(firmware: bytes, firmware_version: int, key: bytes) -> bytes:
    firmware_crc32 = crc32_ieee(firmware)
    header = HEADER_STRUCT.pack(OTA_MAGIC, len(firmware), firmware_crc32, 0)
    prefix = prefix_autenticado(firmware_version, len(firmware), firmware_crc32)
    auth_tag = siphash128(prefix + firmware, key)
    trailer_without_crc = struct.pack(
        "<IIII16s",
        OTA_AUTH_TRAILER_MAGIC,
        OTA_AUTH_TRAILER_VERSION,
        OTA_AUTH_FLAG_SIPHASH128,
        firmware_version & 0xFFFFFFFF,
        auth_tag,
    )
    trailer_crc32 = crc32_ieee(trailer_without_crc)
    trailer = TRAILER_STRUCT.pack(
        OTA_AUTH_TRAILER_MAGIC,
        OTA_AUTH_TRAILER_VERSION,
        OTA_AUTH_FLAG_SIPHASH128,
        firmware_version & 0xFFFFFFFF,
        auth_tag,
        trailer_crc32,
    )
    return header + firmware + trailer


def ota_assinado_verify_package(package: bytes, key: bytes) -> Tuple[int, int, bytes]:
    if len(package) < OTA_HEADER_SIZE + TRAILER_STRUCT.size:
        raise ValueError("Pacote OTA muito pequeno")

    magic, size, crc32_fw, _reserved = HEADER_STRUCT.unpack_from(package, 0)
    if magic not in (0, OTA_MAGIC):
        raise ValueError("Magic OTA invalido: 0x%08X" % magic)

    expected_size = OTA_HEADER_SIZE + size + TRAILER_STRUCT.size
    if len(package) != expected_size:
        raise ValueError("Tamanho total invalido: esperado %d, encontrado %d" % (expected_size, len(package)))

    firmware = package[OTA_HEADER_SIZE:OTA_HEADER_SIZE + size]
    trailer = package[OTA_HEADER_SIZE + size:]
    trailer_magic, trailer_version, flags, firmware_version, auth_tag, trailer_crc32 = TRAILER_STRUCT.unpack(trailer)

    if trailer_magic != OTA_AUTH_TRAILER_MAGIC:
        raise ValueError("Trailer de autenticacao invalido")
    if trailer_version != OTA_AUTH_TRAILER_VERSION:
        raise ValueError("Versao do trailer nao suportada")
    if flags != OTA_AUTH_FLAG_SIPHASH128:
        raise ValueError("Flags do trailer nao suportadas")

    if crc32_ieee(trailer[:-4]) != trailer_crc32:
        raise ValueError("CRC do trailer invalido")

    crc_calculado = crc32_ieee(firmware)
    if crc_calculado != crc32_fw:
        raise ValueError("CRC do firmware invalido")

    prefix = prefix_autenticado(firmware_version, size, crc32_fw)
    auth_calculada = siphash128(prefix + firmware, key)
    if auth_calculada != auth_tag:
        raise ValueError("Tag criptografica invalida")

    return size, firmware_version, auth_tag


def default_key_header() -> pathlib.Path:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    candidates = (
        repo_root / "src" / "bootloader" / "boot_security_config.h",
        repo_root / "bootloader" / "boot_security_config.h",
        pathlib.Path.cwd() / "src" / "bootloader" / "boot_security_config.h",
        pathlib.Path.cwd() / "bootloader" / "boot_security_config.h",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]
