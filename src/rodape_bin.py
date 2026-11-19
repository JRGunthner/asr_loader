"""Metadados dos binários distribuídos pelo build do PR439v3."""

import hashlib
import struct
import zlib

RODAPE = struct.Struct('<8sHHIHBBIHII32sI')
MARCA_RODAPE = b'ASRPROD\0'
TCHE: bytes = b'\0TCHE\0'
TIPOS = ('produção normal', 'produção cripto', 'aplicação', 'bootloader',
         'bootloader cripto', 'OTA simples', 'OTA cripto')
TIPOS_OTA = (5, 6)


def acrescentar_rodape(dados, versao, mcu, tipo, origem, aplicacao):
    """Acrescenta metadados e mantém uma única marca TCHE no fim do pacote."""
    if not dados or not 0 <= versao <= 9999 or mcu not in (1, 2) or not 0 <= tipo < len(TIPOS):
        raise ValueError('Metadados do binário inválidos')

    if tipo in TIPOS_OTA and dados.endswith(TCHE):
        dados = dados[:-len(TCHE)]

    base_otp, versao_otp = (0x10001C00, 1) if tipo in (0, 1) else (0, 0)
    corpo = RODAPE.pack(MARCA_RODAPE, 1, RODAPE.size, len(dados), versao, mcu, tipo,
                        base_otp, versao_otp, origem, aplicacao, hashlib.sha256(dados).digest(), 0)[:-4]

    return dados + corpo + struct.pack('<I', zlib.crc32(corpo)) + TCHE


def separar_rodape(pacote):
    """Valida o rodapé e devolve os bytes originais e seus metadados, quando presentes."""
    tem_tche = pacote.endswith(TCHE)
    fim = len(pacote) - (len(TCHE) if tem_tche else 0)
    inicio = fim - RODAPE.size

    if inicio < 0 or pacote[inicio:inicio + len(MARCA_RODAPE)] != MARCA_RODAPE:
        return pacote, None

    rodape = pacote[inicio:fim]
    (marca, formato, tamanho, quantidade, versao, mcu, tipo, otp, formato_otp,
     origem, aplicacao, digest, crc) = RODAPE.unpack(rodape)
    imagem = pacote[:inicio]

    if (formato != 1 or tamanho != RODAPE.size or quantidade != len(imagem) or not imagem
        or versao > 9999 or mcu not in (1, 2) or tipo >= len(TIPOS)
        or (not tem_tche and tipo not in (0, 1))
        or (tipo > 1 and (otp != 0 or formato_otp != 0))
        or crc != zlib.crc32(rodape[:-4]) or digest != hashlib.sha256(imagem).digest()):
        raise ValueError('Metadados do binário (ASRPROD) inválidos')

    metadados = dict(versao=versao, mcu=mcu, tipo=tipo, otp=otp, formato_otp=formato_otp,
                     origem=origem, aplicacao=aplicacao, marca=marca, versao_rodape=formato,
                     tamanho_rodape=tamanho, tamanho_conteudo=quantidade, sha256=digest,
                     crc32=crc, offset_rodape=inicio)

    return (imagem + TCHE if tipo in TIPOS_OTA else imagem), metadados


def formatar_tabela_rodape(metadados, tamanho_extraido):
    """Lista os campos do rodapé validado com offsets relativos ao seu início."""
    mcu = ('ASR6601CB', 'ASR6601SE')[metadados['mcu'] - 1]
    tipo = TIPOS[metadados['tipo']]

    campos = (
        (0x00, 8, 'Identificador', metadados['marca'].hex(' ').upper()),
        (0x08, 2, 'Versão dos metadados', metadados['versao_rodape']),
        (0x0A, 2, 'Tamanho dos metadados', metadados['tamanho_rodape']),
        (0x0C, 4, 'Tamanho do conteúdo', metadados['tamanho_conteudo']),
        (0x10, 2, 'Versão do firmware', metadados['versao']),
        (0x12, 1, 'Variante ASR', f"{metadados['mcu']} ({mcu})"),
        (0x13, 1, 'Tipo do binário', f"{metadados['tipo']} ({tipo})"),
        (0x14, 4, 'Base do quadro OTP', f"0x{metadados['otp']:08X}"),
        (0x18, 2, 'Versão do quadro OTP', metadados['formato_otp']),
        (0x1A, 4, 'Origem de gravação', f"0x{metadados['origem']:08X}"),
        (0x1E, 4, 'Origem da aplicação', f"0x{metadados['aplicacao']:08X}"),
        (0x22, 32, 'SHA-256 do conteúdo', metadados['sha256'].hex().upper()),
        (0x42, 4, 'CRC-32 dos metadados', f"0x{metadados['crc32']:08X}"),
    )

    linhas = [f"Metadados do binário (ASRPROD) válidos no offset 0x{metadados['offset_rodape']:X} do arquivo.",
              f"{'Offset':<8} {'Bytes':>5}  {'Campo':<23} Valor"]

    linhas.extend(f'0x{offset:02X}     {tamanho:>5}  {campo:<23} {valor}'
                  for offset, tamanho, campo, valor in campos)

    linhas.append(f'Bytes após extração: {tamanho_extraido}')
    return '\n'.join(linhas)
