from __future__ import annotations

import secrets
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .ota_assinado import (
    OTA_AUTH_FLAG_SIPHASH128,
    OTA_AUTH_TRAILER_MAGIC,
    OTA_HEADER_SIZE,
    OTA_MAGIC,
    crc32_ieee,
    default_key_header,
    parse_key_from_header,
    siphash64,
    siphash128,
)

OTA_AUTH_TRAILER_VERSION_LEGADO = 1
OTA_AUTH_TRAILER_VERSION_CRIPTO = 2
OTA_AUTH_FLAG_CRIPTO_SIPHASH64_CTR = 0x00000002
TAMANHO_TRAILER_LEGADO = 36
TAMANHO_TRAILER_CRIPTO = 44


@dataclass(frozen=True)
class PacoteOtaSeguroParseado:
    magic_header: int
    tamanho: int
    crc32_firmware_claro: int
    reservado: int
    versao_trailer: int
    flags: int
    versao_firmware: int
    nonce: bytes
    tag_autenticacao: bytes
    crc32_trailer: int
    firmware_criptografado: bytes


def aplicar_siphash64_ctr_xor(dados: bytes, chave: bytes, nonce: bytes) -> bytes:
    if len(nonce) != 8:
        raise ValueError('O nonce deve ter 8 bytes')

    nonce_u64 = int.from_bytes(nonce, 'little')
    dados_saida = bytearray(dados)
    contador = 0
    posicao = 0
    while posicao < len(dados_saida):
        semente = nonce_u64.to_bytes(8, 'little') + contador.to_bytes(8, 'little')
        fluxo_chave = siphash64(semente, chave, 2).to_bytes(8, 'little')
        tamanho_bloco = min(8, len(dados_saida) - posicao)
        for indice in range(tamanho_bloco):
            dados_saida[posicao + indice] ^= fluxo_chave[indice]
        posicao += tamanho_bloco
        contador += 1
    return bytes(dados_saida)


def caminho_saida_segura_padrao(caminho_firmware: Path) -> Path:
    sufixo = caminho_firmware.suffix or '.bin'
    return caminho_firmware.with_name('%s_ota_cript%s' % (caminho_firmware.stem, sufixo))


def montar_prefixo_seguro(versao_trailer: int, flags: int, versao_firmware: int, tamanho_firmware: int,
                          crc32_firmware_claro: int, nonce: bytes) -> bytes:
    prefixo = struct.pack('<IIIII', versao_trailer, flags, versao_firmware, tamanho_firmware, crc32_firmware_claro)
    if versao_trailer == OTA_AUTH_TRAILER_VERSION_CRIPTO:
        prefixo += nonce
    return prefixo


def montar_pacote_seguro(firmware: bytes, versao_firmware: int, chave: bytes, nonce: Optional[bytes] = None) -> bytes:
    crc32_firmware_claro = crc32_ieee(firmware)
    header = struct.pack('<IIII', OTA_MAGIC, len(firmware), crc32_firmware_claro, 0)
    if nonce is None:
        nonce = secrets.token_bytes(8)
    if len(nonce) != 8:
        raise ValueError('O nonce deve ter 8 bytes')

    flags = OTA_AUTH_FLAG_SIPHASH128 | OTA_AUTH_FLAG_CRIPTO_SIPHASH64_CTR
    firmware_criptografado = aplicar_siphash64_ctr_xor(firmware, chave, nonce)
    prefixo = montar_prefixo_seguro(
        OTA_AUTH_TRAILER_VERSION_CRIPTO,
        flags,
        versao_firmware,
        len(firmware),
        crc32_firmware_claro,
        nonce,
    )
    tag_autenticacao = siphash128(prefixo + firmware_criptografado, chave)
    trailer_sem_crc = struct.pack(
        '<IIII',
        OTA_AUTH_TRAILER_MAGIC,
        OTA_AUTH_TRAILER_VERSION_CRIPTO,
        flags,
        versao_firmware & 0xFFFFFFFF,
    ) + nonce + tag_autenticacao
    crc32_trailer = struct.pack('<I', crc32_ieee(trailer_sem_crc))
    return header + firmware_criptografado + trailer_sem_crc + crc32_trailer


def ler_pacote_seguro(pacote: bytes) -> PacoteOtaSeguroParseado:
    if len(pacote) < OTA_HEADER_SIZE + TAMANHO_TRAILER_LEGADO:
        raise ValueError('Arquivo OTA muito pequeno')

    magic_header, tamanho, crc32_firmware_claro, reservado = struct.unpack_from('<IIII', pacote, 0)
    if magic_header != OTA_MAGIC:
        raise ValueError('magic invalido: 0x%08X' % magic_header)
    if reservado != 0:
        raise ValueError('reserved invalido: 0x%08X' % reservado)

    offset_trailer = OTA_HEADER_SIZE + tamanho
    if offset_trailer + 16 > len(pacote):
        raise ValueError('Arquivo OTA truncado antes do trailer')

    trailer_magic, versao_trailer, flags, versao_firmware = struct.unpack_from('<IIII', pacote, offset_trailer)
    if trailer_magic != OTA_AUTH_TRAILER_MAGIC:
        raise ValueError('trailer_magic invalido: 0x%08X' % trailer_magic)

    firmware_criptografado = pacote[OTA_HEADER_SIZE:offset_trailer]
    if len(firmware_criptografado) != tamanho:
        raise ValueError('Tamanho do payload nao confere com o header')

    if versao_trailer == OTA_AUTH_TRAILER_VERSION_LEGADO:
        tamanho_trailer = TAMANHO_TRAILER_LEGADO
        if offset_trailer + tamanho_trailer != len(pacote):
            raise ValueError('Pacote OTA assinado legado com tamanho inesperado')
        tag_autenticacao = pacote[offset_trailer + 16:offset_trailer + 32]
        crc32_trailer = struct.unpack_from('<I', pacote, offset_trailer + 32)[0]
        nonce = b''
    elif versao_trailer == OTA_AUTH_TRAILER_VERSION_CRIPTO:
        tamanho_trailer = TAMANHO_TRAILER_CRIPTO
        if offset_trailer + tamanho_trailer != len(pacote):
            raise ValueError('Pacote OTA criptografado com tamanho inesperado')
        nonce = pacote[offset_trailer + 16:offset_trailer + 24]
        tag_autenticacao = pacote[offset_trailer + 24:offset_trailer + 40]
        crc32_trailer = struct.unpack_from('<I', pacote, offset_trailer + 40)[0]
    else:
        raise ValueError('Versao de trailer nao suportada: %d' % versao_trailer)

    trailer_sem_crc = pacote[offset_trailer:offset_trailer + tamanho_trailer - 4]
    if crc32_ieee(trailer_sem_crc) != crc32_trailer:
        raise ValueError('CRC do trailer invalido')

    return PacoteOtaSeguroParseado(
        magic_header=magic_header,
        tamanho=tamanho,
        crc32_firmware_claro=crc32_firmware_claro,
        reservado=reservado,
        versao_trailer=versao_trailer,
        flags=flags,
        versao_firmware=versao_firmware,
        nonce=nonce,
        tag_autenticacao=tag_autenticacao,
        crc32_trailer=crc32_trailer,
        firmware_criptografado=firmware_criptografado,
    )


def verificar_pacote_seguro(pacote: bytes, chave: bytes) -> Tuple[PacoteOtaSeguroParseado, bytes]:
    pacote_parseado = ler_pacote_seguro(pacote)

    if pacote_parseado.versao_trailer == OTA_AUTH_TRAILER_VERSION_LEGADO:
        if pacote_parseado.flags != OTA_AUTH_FLAG_SIPHASH128:
            raise ValueError('flags invalidas para trailer legado: 0x%08X' % pacote_parseado.flags)
        prefixo = montar_prefixo_seguro(
            pacote_parseado.versao_trailer,
            pacote_parseado.flags,
            pacote_parseado.versao_firmware,
            pacote_parseado.tamanho,
            pacote_parseado.crc32_firmware_claro,
            b'',
        )
        firmware_claro = pacote_parseado.firmware_criptografado
        tag_autenticacao_esperada = siphash128(prefixo + firmware_claro, chave)
    else:
        flags_esperadas = OTA_AUTH_FLAG_SIPHASH128 | OTA_AUTH_FLAG_CRIPTO_SIPHASH64_CTR
        if pacote_parseado.flags != flags_esperadas:
            raise ValueError('flags invalidas para trailer criptografado: 0x%08X' % pacote_parseado.flags)
        prefixo = montar_prefixo_seguro(
            pacote_parseado.versao_trailer,
            pacote_parseado.flags,
            pacote_parseado.versao_firmware,
            pacote_parseado.tamanho,
            pacote_parseado.crc32_firmware_claro,
            pacote_parseado.nonce,
        )
        tag_autenticacao_esperada = siphash128(prefixo + pacote_parseado.firmware_criptografado, chave)
        firmware_claro = aplicar_siphash64_ctr_xor(pacote_parseado.firmware_criptografado, chave, pacote_parseado.nonce)

    if tag_autenticacao_esperada != pacote_parseado.tag_autenticacao:
        raise ValueError('auth_tag invalida')
    if crc32_ieee(firmware_claro) != pacote_parseado.crc32_firmware_claro:
        raise ValueError('CRC32 do firmware em claro invalido')

    return pacote_parseado, firmware_claro


__all__ = [
    'OTA_AUTH_FLAG_CRIPTO_SIPHASH64_CTR',
    'OTA_AUTH_TRAILER_VERSION_CRIPTO',
    'OTA_AUTH_TRAILER_VERSION_LEGADO',
    'PacoteOtaSeguroParseado',
    'aplicar_siphash64_ctr_xor',
    'caminho_saida_segura_padrao',
    'default_key_header',
    'ler_pacote_seguro',
    'montar_pacote_seguro',
    'montar_prefixo_seguro',
    'parse_key_from_header',
    'verificar_pacote_seguro',
]
