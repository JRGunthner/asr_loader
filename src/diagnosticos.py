import binascii
import json
import os
import pathlib
import struct
from typing import cast

from .constantes import ASR_APP_FLASH_END, ASR_APP_FLASH_START, ARM_SRAM_END, ARM_SRAM_START, OTA_MAGIC

SNAPSHOT_PROFILES = {
    'asr6601': {
        'description': 'Snapshot basico da vector table da aplicacao ASR6601',
        'registers': [
            {'name': 'app_msp', 'address': ASR_APP_FLASH_START},
            {'name': 'app_reset_handler', 'address': ASR_APP_FLASH_START + 4},
            {'name': 'app_nmi_handler', 'address': ASR_APP_FLASH_START + 8},
            {'name': 'app_hardfault_handler', 'address': ASR_APP_FLASH_START + 12},
        ],
    },
    'vector': {
        'description': 'Primeiras palavras da vector table da aplicacao',
        'registers': [
            {'name': 'word_0', 'address': ASR_APP_FLASH_START},
            {'name': 'word_1', 'address': ASR_APP_FLASH_START + 4},
            {'name': 'word_2', 'address': ASR_APP_FLASH_START + 8},
            {'name': 'word_3', 'address': ASR_APP_FLASH_START + 12},
        ],
    },
}


def parse_csv_floats(valor: str) -> list[float]:
    itens = [item.strip() for item in valor.split(',') if item.strip()]
    if not itens:
        raise ValueError('lista de tempos vazia')
    saida = []
    for item in itens:
        numero = float(item)
        if numero < 0:
            raise ValueError('tempos devem ser maiores ou iguais a zero')
        saida.append(numero)
    return saida


def parse_csv_ints(valor: str) -> list[int]:
    itens = [item.strip() for item in valor.split(',') if item.strip()]
    if not itens:
        raise ValueError('lista de valores vazia')
    saida = []
    for item in itens:
        numero = int(item, 0)
        if numero <= 0:
            raise ValueError('valores devem ser maiores que zero')
        saida.append(numero)
    return saida


def crc32_bytes(dados: bytes) -> int:
    return binascii.crc32(dados) & 0xFFFFFFFF


def _check(nome, ok, detalhe, nivel='error'):
    return {
        'name': nome,
        'ok': bool(ok),
        'level': 'ok' if ok else nivel,
        'detail': detalhe,
    }


def _analisar_vetor(nome, valor, app_start, app_end):
    destino = valor & ~0x1
    return {
        'name': nome,
        'raw': valor,
        'target': destino,
        'thumb': bool(valor & 0x01),
        'target_in_app': app_start <= destino < app_end,
    }


def analisar_firmware_bytes(dados: bytes, caminho=None, base_address=ASR_APP_FLASH_START) -> dict:
    formato = 'raw'
    firmware = dados
    warnings = []
    app_start = base_address
    app_end = base_address + (ASR_APP_FLASH_END - ASR_APP_FLASH_START)

    if len(dados) >= 16:
        magic, fw_size, fw_crc, reservado = struct.unpack_from('<IIII', dados, 0)
        tamanho_esperado = 16 + fw_size
        if magic == OTA_MAGIC and reservado == 0 and len(dados) >= tamanho_esperado:
            candidato = dados[16:tamanho_esperado]
            if crc32_bytes(candidato) == fw_crc:
                formato = 'ota_pack'
                firmware = candidato
            else:
                warnings.append('header OTA detectado, mas CRC do payload nao confere; analisando como raw')

    checks = [_check('firmware_nao_vazio', len(firmware) > 0, 'tamanho=%d bytes' % len(firmware)),
              _check('vector_table_minima', len(firmware) >= 16,
                     'necessarios ao menos 16 bytes para MSP/Reset/NMI/HardFault')]

    vetores = []
    if len(firmware) >= 16:
        msp, reset_handler, nmi_handler, hardfault_handler = struct.unpack_from('<IIII', firmware, 0)
        vetores = [
            {'name': 'MSP', 'raw': msp, 'target': msp, 'thumb': False,
             'target_in_app': False, 'target_in_sram': ARM_SRAM_START <= msp < ARM_SRAM_END},
            _analisar_vetor('Reset_Handler', reset_handler, app_start, app_end),
            _analisar_vetor('NMI', nmi_handler, app_start, app_end),
            _analisar_vetor('HardFault', hardfault_handler, app_start, app_end),
        ]
        checks.append(_check('msp_em_sram', vetores[0]['target_in_sram'],
                             'MSP=0x%08X, SRAM=%s-%s' % (msp, hex(ARM_SRAM_START), hex(ARM_SRAM_END))))
        checks.append(_check('reset_thumb', vetores[1]['thumb'],
                             'Reset_Handler=0x%08X precisa ter bit Thumb setado' % reset_handler))
        destino_reset = cast(int, vetores[1]['target'])
        checks.append(_check('reset_na_faixa_app', vetores[1]['target_in_app'],
                             'Reset target=0x%08X, app=%s-%s' % (
                                 destino_reset, hex(app_start), hex(app_end))))

    errors = [item['detail'] for item in checks if not item['ok'] and item['level'] == 'error']
    return {
        'path': str(caminho) if caminho is not None else None,
        'format': formato,
        'base_address': base_address,
        'size': len(firmware),
        'crc32': crc32_bytes(firmware),
        'vectors': vetores,
        'checks': checks,
        'warnings': warnings,
        'errors': errors,
    }


def analisar_firmware(caminho, base_address=ASR_APP_FLASH_START) -> dict:
    caminho_firmware = pathlib.Path(caminho)
    if not caminho_firmware.is_file():
        raise FileNotFoundError('ERROR: arquivo nao encontrado: %s' % caminho_firmware)
    return analisar_firmware_bytes(
        caminho_firmware.read_bytes(),
        caminho=caminho_firmware,
        base_address=base_address,
    )


def imprimir_relatorio_firmware(relatorio):
    print('Firmware : %s' % relatorio['path'])
    print('Formato  : %s' % relatorio['format'])
    print('Tamanho  : %d bytes (0x%X)' % (relatorio['size'], relatorio['size']))
    print('CRC32    : 0x%08X' % relatorio['crc32'])
    for aviso in relatorio['warnings']:
        print('Aviso    : %s' % aviso)
    if relatorio['vectors']:
        print('Vector table:')
        for vetor in relatorio['vectors']:
            print('  %-14s raw=0x%08X target=0x%08X thumb=%s' % (
                vetor['name'],
                vetor['raw'],
                vetor['target'],
                'sim' if vetor['thumb'] else 'nao',
            ))
    print('Checks:')
    for item in relatorio['checks']:
        print('  [%s] %s - %s' % ('OK' if item['ok'] else item['level'].upper(), item['name'], item['detail']))


def montar_prevalidar_flash(addr_file, strict_app_range=False) -> dict:
    erros = []
    avisos = []
    itens = []

    if len(addr_file) % 2 != 0:
        erros.append('informe pares <address> <filename>')
        return {'items': itens, 'warnings': avisos, 'errors': erros, 'total_size': 0}

    for indice in range(0, len(addr_file), 2):
        endereco_texto = addr_file[indice]
        caminho_texto = addr_file[indice + 1]
        try:
            endereco = int(endereco_texto, 0)
        except ValueError:
            erros.append('o endereco "%s" deve ser um numero' % endereco_texto)
            continue

        caminho = pathlib.Path(caminho_texto)
        if not caminho.is_file():
            erros.append('arquivo nao encontrado: %s' % caminho)
            continue
        if not os.access(str(caminho), os.R_OK):
            erros.append('falha na leitura do arquivo: %s' % caminho)
            continue

        dados = caminho.read_bytes()
        tamanho = len(dados)
        fim = endereco + tamanho
        fora_app = not (ASR_APP_FLASH_START <= endereco < ASR_APP_FLASH_END and fim <= ASR_APP_FLASH_END)
        if fora_app:
            mensagem = '%s em 0x%08X-0x%08X fora da faixa app %s-%s' % (
                caminho, endereco, fim, hex(ASR_APP_FLASH_START), hex(ASR_APP_FLASH_END))
            if strict_app_range:
                erros.append(mensagem)
            else:
                avisos.append(mensagem)

        itens.append({
            'address': endereco,
            'end_address': fim,
            'path': str(caminho),
            'size': tamanho,
            'crc32': crc32_bytes(dados),
        })

    ordenados = sorted(itens, key=lambda item: item['address'])
    for anterior, atual in zip(ordenados, ordenados[1:]):
        if atual['address'] < anterior['end_address']:
            erros.append('overlap entre %s e %s' % (anterior['path'], atual['path']))

    return {
        'items': itens,
        'warnings': avisos,
        'errors': erros,
        'total_size': sum(item['size'] for item in itens),
    }


def imprimir_prevalidar_flash(relatorio):
    print('Pré-validação da flash:')
    for item in relatorio['items']:
        print('  0x%08X-0x%08X  %8d bytes  CRC32=0x%08X  %s' % (
            item['address'],
            item['end_address'],
            item['size'],
            item['crc32'],
            item['path'],
        ))
    for aviso in relatorio['warnings']:
        print('Aviso: %s' % aviso)
    for erro in relatorio['errors']:
        print('Erro : %s' % erro)
    print('Total: %d bytes' % relatorio['total_size'])


def carregar_snapshot_profile(profile):
    caminho = pathlib.Path(profile)
    if caminho.is_file():
        dados = json.loads(caminho.read_text(encoding='utf-8'))
    else:
        if profile not in SNAPSHOT_PROFILES:
            raise ValueError('ERROR: perfil de snapshot nao encontrado: %s' % profile)
        dados = SNAPSHOT_PROFILES[profile]

    registros = []
    for item in dados.get('registers', []):
        endereco = item['address']
        registros.append({
            'name': item['name'],
            'address': int(endereco, 0) if isinstance(endereco, str) else endereco,
        })
    if not registros:
        raise ValueError('ERROR: perfil de snapshot sem registros')
    return {
        'name': profile,
        'description': dados.get('description', ''),
        'registers': registros,
    }


def imprimir_snapshot(relatorio):
    print('Snapshot: %s' % relatorio['profile'])
    if relatorio.get('description'):
        print('Descricao: %s' % relatorio['description'])
    for item in relatorio['registers']:
        if item['ok']:
            print('  %-24s 0x%08X = 0x%08X' % (item['name'], item['address'], item['value']))
        else:
            print('  %-24s 0x%08X = ERROR: %s' % (item['name'], item['address'], item['error']))
