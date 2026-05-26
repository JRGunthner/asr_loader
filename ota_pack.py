#!/usr/bin/env python3
"""
ota_pack.py - Empacota um firmware .bin para OTA via flash externa.

Uso:
    python ota_pack.py <firmware.bin> [saida.bin]

Exemplo:
    python ota_pack.py release\\postyou.bin release\\postyou_ota.bin

O arquivo de saida deve ser gravado a partir do endereco 0x00000000
da flash externa (SPI). O formato e:

    [0x00] magic     = 0xB00710AD  (4 bytes, little-endian)
    [0x04] size      = tamanho do firmware em bytes  (4 bytes, LE)
    [0x08] crc32     = CRC-32/ISO-HDLC do firmware  (4 bytes, LE)
    [0x0C] reserved  = 0x00000000  (4 bytes)
    [0x10] firmware data...

O CRC32 utilizado e o padrao IEEE 802.3 (mesmo do ETH/ZIP/PNG),
identico ao CRC-32 configurado no hardware do ASR6601.
"""

import sys
import struct
import binascii
import os

OTA_MAGIC = 0xB00710AD


def pack(fw_path_pack: str, out_path_pack: str) -> None:
    with open(fw_path_pack, "rb") as f:
        fw_data = f.read()

    fw_size = len(fw_data)
    fw_crc  = binascii.crc32(fw_data) & 0xFFFFFFFF

    header = struct.pack("<IIII", OTA_MAGIC, fw_size, fw_crc, 0)

    with open(out_path_pack, "wb") as f:
        f.write(header)
        f.write(fw_data)

    print(f"Firmware : {fw_path_pack}")
    print(f"Tamanho  : {fw_size} bytes (0x{fw_size:X})")
    print(f"CRC32    : 0x{fw_crc:08X}")
    print(f"Saida    : {out_path_pack}  ({len(header) + fw_size} bytes no total)")
    print()
    print("Grave o arquivo de saida a partir do endereco 0x00000000 da flash externa.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    fw_path  = sys.argv[1]
    base, ext = os.path.splitext(fw_path)
    out_path = sys.argv[2] if len(sys.argv) >= 3 else f"{base}_ota{ext}"

    if not os.path.isfile(fw_path):
        print(f"Erro: arquivo nao encontrado: {fw_path}")
        sys.exit(1)

    pack(fw_path, out_path)
