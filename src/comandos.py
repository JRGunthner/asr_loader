import binascii
import contextlib
import io
import json
import os
import pathlib
import struct
import time
from typing import TypedDict
from .constantes import (
    ASR_APP_FLASH_END,
    ASR_APP_FLASH_START,
    ARM_SRAM_END,
    ARM_SRAM_START,
    EEPROM_ENDERECO_ASR6601CB,
    EEPROM_ENDERECO_ASR6601SE,
    EEPROM_ENDERECO_V8_ASR6601CB,
    EEPROM_ENDERECO_V8_ASR6601SE,
    EEPROM_SIZE,
    EEPROM_SIZE_V8,
    OTA_MAGIC,
)
from .diagnosticos import (
    analisar_firmware,
    carregar_snapshot_profile,
    imprimir_prevalidar_flash,
    imprimir_relatorio_firmware,
    imprimir_snapshot,
    montar_prevalidar_flash,
    parse_csv_floats,
    parse_csv_ints,
)
from .exceptions import CmdExcessao
from .ota_assinado import build_ota_assinado_package, crc32_ieee, default_key_header, parse_key_from_header, \
    ota_assinado_verify_package, append_ota_tche_sufixo, split_ota_tche_sufixo
from .ota_pacote_cripto import caminho_saida_segura_padrao, montar_pacote_seguro, verificar_pacote_seguro
from .utils import get_crc32


def asr_fechar_porta(processador):
    if processador.ser is None:
        return
    try:
        processador.ser.close()
    except OSError:
        pass
    processador.ser = None


class AsrOtaPackInfo(TypedDict):
    caminho: str
    pacote: bytes
    firmware: bytes
    magic: int
    fw_size: int
    fw_crc: int
    reservado: int


def asr_conectar(processador, lista_portas, baud):
    if not lista_portas:
        raise CmdExcessao('ERROR: nenhuma porta serial disponivel')

    erros = []
    for porta in reversed(lista_portas):
        print("Serial port %s" % porta)
        try:
            processador.set_port(porta)
            processador.conectar()
            processador.set_baudrate(baud)
            return True
        except Exception as excessao:
            print("Nao foi possivel conectar em %s: %s" % (porta, excessao))
            erros.append('%s: %s' % (porta, excessao))
            asr_fechar_porta(processador)
    raise CmdExcessao('ERROR: nao foi possivel conectar (%s)' % '; '.join(erros))


def _asr_conectar_quiet(processador, lista_portas, baud, quiet=False):
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            return asr_conectar(processador, lista_portas, baud)
    return asr_conectar(processador, lista_portas, baud)


def asr_prevalidar_flash(param):
    relatorio = montar_prevalidar_flash(
        param.addr_file,
        strict_app_range=getattr(param, 'strict_app_range', False),
    )
    if getattr(param, 'json', False):
        print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    else:
        imprimir_prevalidar_flash(relatorio)

    if relatorio['errors']:
        raise Exception('ERROR: pré-validação falhou: %s' % '; '.join(relatorio['errors']))
    return relatorio


def asr_firmware_inspect(param):
    relatorio = analisar_firmware(param.firmware, base_address=param.base_address)
    if getattr(param, 'json', False):
        print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    else:
        imprimir_relatorio_firmware(relatorio)

    if getattr(param, 'strict', False) and relatorio['errors']:
        raise Exception('ERROR: firmware_inspect falhou: %s' % '; '.join(relatorio['errors']))
    return relatorio


def asr_erase(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.erase(param.address, param.size)
    processador.sw_reset(0)


def asr_apagar_eeprom(processador, mostrar_erros=True, mostrar_identificacao=True, v8=False):
    if v8:
        enderecos_eeprom = (
            ("ASR6601CB", EEPROM_ENDERECO_V8_ASR6601CB),
            ("ASR6601SE", EEPROM_ENDERECO_V8_ASR6601SE),
        )
        tamanho_eeprom = EEPROM_SIZE_V8
    else:
        enderecos_eeprom = (
            ("ASR6601CB", EEPROM_ENDERECO_ASR6601CB),
            ("ASR6601SE", EEPROM_ENDERECO_ASR6601SE),
        )
        tamanho_eeprom = EEPROM_SIZE
    variantes_detectadas = []
    falhas = []

    for variante, endereco in enderecos_eeprom:
        try:
            processador.erase(endereco, tamanho_eeprom)
            variantes_detectadas.append(variante)
        except Exception as excessao:
            if mostrar_erros:
                print('Aviso: nao foi possivel apagar EEPROM para %s em %s: %s' % (variante, hex(endereco), excessao))
            falhas.append((variante, excessao))

    if len(falhas) == len(enderecos_eeprom):
        raise Exception('ERROR: falha ao apagar EEPROM em todos os mapeamentos testados')

    if len(variantes_detectadas) == 1:
        variante_detectada = variantes_detectadas[0]
    elif len(variantes_detectadas) > 1:
        variante_detectada = variantes_detectadas[1]
    else:
        raise Exception('ERROR: nenhum mapeamento de EEPROM foi identificado')

    if mostrar_identificacao:
        print('Dispositivo identificado: %s' % variante_detectada)
    return variante_detectada


def asr_identificar_mcu(param, processador, config):
    """Identifica o MCU pelo mesmo teste de mapeamento usado no flash."""
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return None

    variante = asr_apagar_eeprom(
        processador,
        mostrar_erros=False,
        mostrar_identificacao=False,
        v8=getattr(config, 'v8', False),
    )
    flash_size = 128 * 1024 if variante == 'ASR6601CB' else 256 * 1024

    print('MCU identificado: %s (%d KiB de flash)' % (variante, flash_size // 1024))
    return variante


def asr_obter_mapa_memoria(variante, v8=False):
    if variante == 'ASR6601CB':
        flash_size = 128 * 1024
        sram_size = 16 * 1024
        eeprom_address = EEPROM_ENDERECO_ASR6601CB
    elif variante == 'ASR6601SE':
        flash_size = 256 * 1024
        sram_size = 64 * 1024
        eeprom_address = EEPROM_ENDERECO_ASR6601SE
    else:
        raise Exception('ERROR: variante de MCU desconhecida: %s' % variante)

    if v8:
        eeprom_address = (EEPROM_ENDERECO_V8_ASR6601CB if variante == 'ASR6601CB'
                          else EEPROM_ENDERECO_V8_ASR6601SE)
        eeprom_size = EEPROM_SIZE_V8
    else:
        eeprom_size = EEPROM_SIZE

    return (
        ('Flash interna', ASR_APP_FLASH_START, ASR_APP_FLASH_START + flash_size, flash_size),
        ('SRAM', ARM_SRAM_START, ARM_SRAM_START + sram_size, sram_size),
        ('EEPROM emulada', eeprom_address, eeprom_address + eeprom_size, eeprom_size),
    )


def asr_mapa_memoria(param, processador, config, espaco=None, ler_bytes=False):
    """Mostra ou le um espaco de memoria para o MCU conectado."""
    mcu_informado = getattr(param, 'mcu', None)
    if mcu_informado:
        variantes = {'cb': 'ASR6601CB', 'se': 'ASR6601SE'}
        variante = variantes[mcu_informado]
        if not asr_conectar(processador, config.portas_disponiveis, param.baud):
            return b'' if ler_bytes else ()
        print('MCU selecionado: %s' % variante)
    else:
        variante = asr_identificar_mcu(param, processador, config)
    if variante is None:
        return b'' if ler_bytes else ()

    mapa = asr_obter_mapa_memoria(variante, v8=getattr(config, 'v8', False))
    if espaco is not None:
        mapa = tuple(regiao for regiao in mapa if regiao[0] == espaco)

    for nome, inicio, fim, tamanho in mapa:
        print('%s: 0x%08X - 0x%08X (%d KiB)' % (
            nome,
            inicio,
            fim - 1,
            tamanho // 1024,
        ))

    if ler_bytes:
        if len(mapa) != 1:
            raise Exception('ERROR: leitura de bytes requer um espaco de memoria especifico')
        nome, inicio, _fim, tamanho = mapa[0]
        nomes_dump = {
            'Flash interna': 'mapa_flash.bin',
            'SRAM': 'mapa_sram.bin',
            'EEPROM emulada': 'mapa_eeprom.bin',
        }
        output = getattr(param, 'output', None) or str(
            pathlib.Path('mapas_memoria') / nomes_dump[nome]
        )
        return _asr_ler_mem(processador, inicio, tamanho, output)
    return mapa


def asr_clean_eeprom(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    asr_apagar_eeprom(processador, v8=getattr(config, 'v8', False))
    processador.sw_reset(0)


def asr_flash(param, processador, config):
    relatorio_prevalidar = montar_prevalidar_flash(param.addr_file)
    if relatorio_prevalidar['errors']:
        imprimir_prevalidar_flash(relatorio_prevalidar)
        raise Exception('ERROR: pré-validação falhou: %s' % '; '.join(relatorio_prevalidar['errors']))
    quantidade_arquivos = len(relatorio_prevalidar['items'])
    rotulo_arquivo = 'arquivo' if quantidade_arquivos == 1 else 'arquivos'
    print('Pré-validação TRI: %d %s, %d bytes' % (
        quantidade_arquivos,
        rotulo_arquivo,
        relatorio_prevalidar['total_size'],
    ))
    for aviso in relatorio_prevalidar['warnings']:
        print('Aviso: %s' % aviso)
    arquivos = [(item['address'], item['path']) for item in relatorio_prevalidar['items']]

    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return False

    if config.apaga_eeprom:
        asr_apagar_eeprom(processador, mostrar_erros=False, v8=getattr(config, 'v8', False))

    for endereco, pacote in arquivos:
        pacote_len = os.path.getsize(pacote)
        crc_pacote = get_crc32(pacote)
        processador.erase(endereco, pacote_len)

        endereco_na_flash = endereco

        if config.verbose:
            print('Gravando', ' %s no endereco %s...' % (pacote, hex(endereco)))
        else:
            print('Gravando', end='', flush=True)

        with open(pacote, 'rb') as arquivo:
            while True:
                line_data = arquivo.read(512)
                if line_data == b'':
                    break

                processador.flash(endereco_na_flash, line_data)
                endereco_na_flash += len(line_data)
                if not config.verbose:
                    print('.', end='', flush=True)

        processador.verify(endereco, pacote_len, crc_pacote)

    if not config.verbose:
        print('.')

    processador.sw_reset(0)
    return True


def asr_escrever_otp(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_otp(param.address, binascii.unhexlify(param.data))


def asr_ler_otp(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.ler_otp(param.address, param.size)


def asr_escrever_opt0(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_opt0(param.opt0_l, param.opt0_h)


def asr_ler_opt0(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt0()


def asr_escrever_opt1(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_opt1(param.opt1_l, param.opt1_h)


def asr_ler_opt1(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt1()


def asr_serial_asr(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.serial_asr()


def asr_sw_reset(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.sw_reset(0)


def asr_hw_reset(param, processador, config):
    if not config.portas_disponiveis:
        raise CmdExcessao('ERROR: nenhuma porta serial disponivel')

    erros = []
    for porta in reversed(config.portas_disponiveis):
        print("Serial port %s" % porta)
        try:
            processador.set_port(porta, param.baud)
            processador.hw_reset(1 if param.boot else 0)
            asr_fechar_porta(processador)
            return True
        except Exception as excessao:
            print("Nao foi possivel resetar via hardware em %s: %s" % (porta, excessao))
            erros.append('%s: %s' % (porta, excessao))
            asr_fechar_porta(processador)
    raise CmdExcessao('ERROR: nao foi possivel resetar via hardware (%s)' % '; '.join(erros))


def asr_controlar_linha_serial(param, processador, config):
    if param.hold is not None and param.hold < 0:
        raise Exception('ERROR: --hold deve ser maior ou igual a zero')

    if not config.portas_disponiveis:
        raise CmdExcessao('ERROR: nenhuma porta serial disponivel')

    erros = []
    for porta in reversed(config.portas_disponiveis):
        print("Serial port %s" % porta)
        try:
            processador.set_port(porta, param.baud)
            if param.control_line == 'dtr':
                processador.set_dtr(param.control_state)
            elif param.control_line == 'rts':
                processador.set_rts(param.control_state)
            else:
                raise Exception('linha serial invalida: %s' % param.control_line)

            print('%s=%d em %s' % (param.control_line.upper(), 1 if param.control_state else 0, porta))
            if param.hold is None:
                print('Mantendo a porta aberta. Pressione Ctrl+C para sair.')
                while True:
                    time.sleep(1)
            elif param.hold > 0:
                time.sleep(param.hold)

            asr_fechar_porta(processador)
            return True
        except KeyboardInterrupt:
            print('')
            asr_fechar_porta(processador)
            return True
        except Exception as excessao:
            asr_fechar_porta(processador)
            print("Nao foi possivel controlar linha em %s: %s" % (porta, excessao))
            erros.append('%s: %s' % (porta, excessao))
    raise CmdExcessao('ERROR: nao foi possivel controlar linha serial (%s)' % '; '.join(erros))


def asr_probe(param, processador, config):
    asr_conectar(processador, config.portas_disponiveis, param.baud)
    return True


def asr_probe_sweep(param, processador_factory, config):
    reset_delays = parse_csv_floats(param.sweep_reset_delays)
    release_delays = parse_csv_floats(param.sweep_release_delays)
    bauds = parse_csv_ints(param.sweep_bauds)
    resultados = []
    reset_original = config.boot_reset_delay
    release_original = config.boot_release_delay

    try:
        for baud in bauds:
            for reset_delay in reset_delays:
                for release_delay in release_delays:
                    config.boot_reset_delay = reset_delay
                    config.boot_release_delay = release_delay
                    processador = processador_factory()
                    inicio = time.perf_counter()
                    erro = None
                    ok = False
                    try:
                        _asr_conectar_quiet(processador, config.portas_disponiveis, baud, quiet=True)
                        ok = True
                    except Exception as excessao:
                        erro = str(excessao)
                    finally:
                        asr_fechar_porta(processador)

                    resultados.append({
                        'ok': ok,
                        'baud': baud,
                        'boot_reset_delay': reset_delay,
                        'boot_release_delay': release_delay,
                        'duration_ms': round((time.perf_counter() - inicio) * 1000, 3),
                        'error': erro,
                    })
    finally:
        config.boot_reset_delay = reset_original
        config.boot_release_delay = release_original

    if getattr(param, 'json', False):
        print(json.dumps({'results': resultados}, indent=2, ensure_ascii=False))
    else:
        print('Teste de boot sweep:')
        for item in resultados:
            print('  %-4s baud=%d reset=%.3fs release=%.3fs dur=%.3fms %s' % (
                'OK' if item['ok'] else 'FAIL',
                item['baud'],
                item['boot_reset_delay'],
                item['boot_release_delay'],
                item['duration_ms'],
                item['error'] or '',
            ))

    if not any(item['ok'] for item in resultados):
        raise CmdExcessao('ERROR: teste de boot sweep falhou em todas as combinacoes')
    return resultados


def asr_verify(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return

    image_checksum = get_crc32(param.filename)
    image_size = os.path.getsize(param.filename)

    print('Verificando %s no endereco %s...' % (param.filename, hex(param.address)))
    processador.verify(param.address, image_size, image_checksum)


def asr_versao_bootloader(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return (0,)
    return processador.versao_bootloader()


def asr_ler_reg(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return (0,)
    return processador.ler_reg(param.address)


def asr_formatar_hexdump(endereco_inicial, dados):
    linhas = []
    for offset in range(0, len(dados), 16):
        bloco = dados[offset:offset + 16]
        hex_bytes = ' '.join('%02X' % byte for byte in bloco)
        hex_bytes = hex_bytes.ljust(16 * 3 - 1)
        ascii_bytes = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in bloco)
        linhas.append('%08X  %s  |%s|' % (endereco_inicial + offset, hex_bytes, ascii_bytes))
    return '\n'.join(linhas)


def asr_ota_pack_ler_info(caminho_pacote) -> AsrOtaPackInfo:
    if not os.path.isfile(caminho_pacote):
        raise Exception('ERROR: arquivo nao encontrado: %s' % caminho_pacote)

    with open(caminho_pacote, 'rb') as arquivo:
        pacote = arquivo.read()

    if len(pacote) < 16:
        raise Exception('ERROR: pacote OTA muito pequeno')

    magic, fw_size, fw_crc, reservado = struct.unpack_from('<IIII', pacote, 0)

    if magic != OTA_MAGIC:
        raise Exception('ERROR: magic OTA invalido: 0x%08X' % magic)

    if reservado != 0:
        raise Exception('ERROR: campo reservado invalido: 0x%08X' % reservado)

    tamanho_esperado = 16 + fw_size
    try:
        pacote = split_ota_tche_sufixo(pacote, tamanho_esperado)
    except ValueError as excessao:
        raise Exception('ERROR: %s' % excessao)

    firmware = pacote[16:]
    crc_calculado = binascii.crc32(firmware) & 0xFFFFFFFF
    if crc_calculado != fw_crc:
        raise Exception(
            'ERROR: CRC32 do firmware invalido: esperado 0x%08X, calculado 0x%08X' % (fw_crc, crc_calculado))

    return {
        'caminho': caminho_pacote,
        'pacote': pacote,
        'firmware': firmware,
        'magic': magic,
        'fw_size': fw_size,
        'fw_crc': fw_crc,
        'reservado': reservado,
    }


def asr_endereco_em_faixa_app(endereco):
    return ASR_APP_FLASH_START <= endereco < ASR_APP_FLASH_END


def asr_endereco_em_sram(endereco):
    return ARM_SRAM_START <= endereco < ARM_SRAM_END


def asr_imprimir_analise_vetor(nome, valor):
    destino = valor & ~0x1
    thumb_setado = bool(valor & 0x1)
    print('%s      : 0x%08X' % (nome, valor))
    print('  Thumb setado : %s' % ('sim' if thumb_setado else 'nao'))
    print('  Destino      : 0x%08X' % destino)
    print('  Faixa da app : %s (%s - %s)' % (
        'sim' if asr_endereco_em_faixa_app(destino) else 'nao',
        hex(ASR_APP_FLASH_START),
        hex(ASR_APP_FLASH_END),
    ))


def asr_ler_mem(param, processador, config):
    if param.size <= 0:
        raise Exception('ERROR: o tamanho deve ser maior que zero')

    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return b''

    return _asr_ler_mem(processador, param.address, param.size, getattr(param, 'output', None))


def _asr_ler_mem(processador, endereco_inicial, tamanho, output=None):
    try:
        endereco_alinhado = endereco_inicial & ~0x3
        deslocamento_inicial = endereco_inicial - endereco_alinhado
        tamanho_total = deslocamento_inicial + tamanho
        quantidade_palavras = (tamanho_total + 3) // 4

        dados = bytearray()
        linha = bytearray()

        print('Lendo memoria: %d bytes a partir de %s' % (tamanho, hex(endereco_inicial)))
        if output:
            pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
        with (open(output, 'wb') if output else contextlib.nullcontext()) as arquivo:
            for indice in range(quantidade_palavras):
                endereco_atual = endereco_alinhado + (indice * 4)
                palavra = struct.pack('<I', processador.ler_reg(endereco_atual)[0])
                inicio_palavra = indice * 4
                inicio = max(deslocamento_inicial, inicio_palavra)
                fim = min(deslocamento_inicial + tamanho, inicio_palavra + len(palavra))
                if inicio >= fim:
                    continue

                trecho = palavra[inicio - inicio_palavra:fim - inicio_palavra]
                dados.extend(trecho)
                if arquivo:
                    arquivo.write(trecho)

                while trecho:
                    quantidade = min(16 - len(linha), len(trecho))
                    linha.extend(trecho[:quantidade])
                    trecho = trecho[quantidade:]
                    if len(linha) == 16:
                        endereco_linha = endereco_inicial + len(dados) - len(trecho) - len(linha)
                        print(asr_formatar_hexdump(endereco_linha, bytes(linha)), flush=True)
                        linha.clear()

            if linha:
                print(asr_formatar_hexdump(endereco_inicial + len(dados) - len(linha), bytes(linha)), flush=True)

        print('Leitura de memoria concluida: %d bytes a partir de %s' % (tamanho, hex(endereco_inicial)))
        if output:
            print('Dump salvo em: %s' % output)

        return bytes(dados)
    finally:
        processador.sw_reset(0)


def asr_snapshot(param, processador, config):
    perfil = carregar_snapshot_profile(param.profile)
    _asr_conectar_quiet(processador, config.portas_disponiveis, param.baud, quiet=getattr(param, 'json', False))

    registros = []
    for item in perfil['registers']:
        try:
            valor = processador.ler_reg(item['address'])[0]
            registros.append({
                'name': item['name'],
                'address': item['address'],
                'value': valor,
                'ok': True,
            })
        except Exception as excessao:
            registros.append({
                'name': item['name'],
                'address': item['address'],
                'error': str(excessao),
                'ok': False,
            })

    relatorio = {
        'profile': perfil['name'],
        'description': perfil['description'],
        'registers': registros,
    }
    if getattr(param, 'output', None):
        pathlib.Path(param.output).write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding='utf-8')
    if getattr(param, 'json', False):
        print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    else:
        imprimir_snapshot(relatorio)
    return relatorio


def asr_escrever_reg(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_reg(param.address, param.value)


def asr_jump(param, processador, config):
    if not asr_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.jump(param.address)


def asr_ota_pack(param):
    fw_path = param.firmware
    if not os.path.isfile(fw_path):
        raise Exception('ERROR: arquivo nao encontrado: %s' % fw_path)

    if param.output is None:
        base, ext = os.path.splitext(fw_path)
        out_path = '%s_ota%s' % (base, ext)
    else:
        out_path = param.output

    with open(fw_path, 'rb') as arquivo:
        fw_data = arquivo.read()

    fw_size = len(fw_data)
    fw_crc = binascii.crc32(fw_data) & 0xFFFFFFFF
    header = struct.pack('<IIII', OTA_MAGIC, fw_size, fw_crc, 0)
    pacote = append_ota_tche_sufixo(header + fw_data)

    with open(out_path, 'wb') as arquivo:
        arquivo.write(pacote)

    print('Firmware : %s' % fw_path)
    print('Tamanho  : %d bytes (0x%X)' % (fw_size, fw_size))
    print('CRC32    : 0x%08X' % fw_crc)
    print('Saida    : %s  (%d bytes no total)' % (out_path, len(pacote)))
    print('Grave o arquivo de saida a partir do endereco 0x00000000 da flash externa.')


def asr_ota_pack_verify(param):
    info = asr_ota_pack_ler_info(param.input)

    print('Pacote    : %s' % info['caminho'])
    print('Magic     : 0x%08X' % info['magic'])
    print('Tamanho   : %d bytes (0x%X)' % (info['fw_size'], info['fw_size']))
    print('CRC32     : 0x%08X' % info['fw_crc'])
    print('Reservado : 0x%08X' % info['reservado'])


def asr_ota_pack_inspect(param):
    info = asr_ota_pack_ler_info(param.input)
    firmware = info['firmware']
    vector_table = firmware[:64]

    print('Header OTA:')
    print('  Pacote    : %s' % info['caminho'])
    print('  Magic     : 0x%08X' % info['magic'])
    print('  Tamanho   : %d bytes (0x%X)' % (info['fw_size'], info['fw_size']))
    print('  CRC32     : 0x%08X' % info['fw_crc'])
    print('  Reservado : 0x%08X' % info['reservado'])

    print('\nVector table (primeiros %d bytes):' % len(vector_table))
    if vector_table:
        print(asr_formatar_hexdump(ASR_APP_FLASH_START, vector_table))
    else:
        print('<firmware vazio>')

    print('\nAnalise basica estrutural:')
    print('  Tamanho da vector table analisada : %d bytes' % len(vector_table))
    print('  Cabecalho OTA valido              : sim')
    print('  CRC32 do firmware valido          : sim')

    if len(firmware) < 16:
        print('  Vector table incompleta: sao necessarios ao menos 16 bytes para MSP/Reset/NMI/HardFault')
        return

    msp, reset_handler, nmi_handler, hardfault_handler = struct.unpack_from('<IIII', firmware, 0)
    print('  MSP            : 0x%08X' % msp)
    print('    Faixa SRAM   : %s (%s - %s)' % (
        'sim' if asr_endereco_em_sram(msp) else 'nao',
        hex(ARM_SRAM_START),
        hex(ARM_SRAM_END),
    ))
    asr_imprimir_analise_vetor('  Reset_Handler', reset_handler)
    asr_imprimir_analise_vetor('  NMI', nmi_handler)
    asr_imprimir_analise_vetor('  HardFault', hardfault_handler)


def asr_ota_assinado(param):
    fw_path = param.firmware
    if not os.path.isfile(fw_path):
        raise Exception('ERROR: arquivo nao encontrado: %s' % fw_path)

    if param.output is None:
        base, ext = os.path.splitext(fw_path)
        out_path = '%s_ota_assinado%s' % (base, ext)
    else:
        out_path = param.output

    key_header = pathlib.Path(
        param.key_header).resolve() if param.key_header is not None else default_key_header().resolve()
    key = parse_key_from_header(key_header)

    with open(fw_path, 'rb') as arquivo:
        fw_data = arquivo.read()

    package = build_ota_assinado_package(fw_data, param.firmware_version, key)

    with open(out_path, 'wb') as arquivo:
        arquivo.write(package)

    _size, _version, auth_tag = ota_assinado_verify_package(package, key)

    print('Firmware : %s' % fw_path)
    print('Tamanho  : %d bytes (0x%X)' % (len(fw_data), len(fw_data)))
    print('CRC32    : 0x%08X' % crc32_ieee(fw_data))
    print('Versao   : %d' % param.firmware_version)
    print('AuthTag  : %s' % auth_tag.hex())
    print('Chave    : %s' % key_header)
    print('Saida    : %s  (%d bytes no total)' % (out_path, len(package)))
    print('Grave o arquivo de saida a partir do endereco 0x00000000 da flash externa.')


def asr_ota_assinado_verify(param):
    package_path = param.input
    if not os.path.isfile(package_path):
        raise Exception('ERROR: arquivo nao encontrado: %s' % package_path)

    key_header = pathlib.Path(
        param.key_header).resolve() if param.key_header is not None else default_key_header().resolve()
    key = parse_key_from_header(key_header)

    with open(package_path, 'rb') as arquivo:
        package = arquivo.read()

    size, version, auth_tag = ota_assinado_verify_package(package, key)

    print('Pacote   : %s' % package_path)
    print('Firmware : %d bytes (0x%X)' % (size, size))
    print('Versao   : %d' % version)
    print('AuthTag  : %s' % auth_tag.hex())
    print('Chave    : %s' % key_header)


def asr_ota_cript(param):
    caminho_firmware = pathlib.Path(param.firmware)
    if not caminho_firmware.is_file():
        raise Exception('ERROR: arquivo nao encontrado: %s' % caminho_firmware)

    caminho_saida = pathlib.Path(param.output) if param.output is not None else caminho_saida_segura_padrao(
        caminho_firmware)
    cabecalho_chave = pathlib.Path(
        param.key_header).resolve() if param.key_header is not None else default_key_header().resolve()
    chave = parse_key_from_header(cabecalho_chave)
    dados_firmware = caminho_firmware.read_bytes()

    pacote = montar_pacote_seguro(dados_firmware, param.firmware_version, chave)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_saida.write_bytes(pacote)

    pacote_parseado, _firmware_claro = verificar_pacote_seguro(pacote, chave)

    print('Firmware : %s' % caminho_firmware)
    print('Tamanho  : %d bytes (0x%X)' % (len(dados_firmware), len(dados_firmware)))
    print('CRC32    : 0x%08X' % crc32_ieee(dados_firmware))
    print('Versao   : %d' % pacote_parseado.versao_firmware)
    print('Flags    : 0x%08X' % pacote_parseado.flags)
    print('Nonce    : %s' % pacote_parseado.nonce.hex())
    print('AuthTag  : %s' % pacote_parseado.tag_autenticacao.hex())
    print('Chave    : %s' % cabecalho_chave)
    print('Saida    : %s  (%d bytes no total)' % (caminho_saida, len(pacote)))
    print('Grave o arquivo de saida a partir do endereco 0x00000000 da flash externa.')


def asr_ota_ota_verify(param):
    caminho_pacote = pathlib.Path(param.input)
    if not caminho_pacote.is_file():
        raise Exception('ERROR: arquivo nao encontrado: %s' % caminho_pacote)

    cabecalho_chave = pathlib.Path(
        param.key_header).resolve() if param.key_header is not None else default_key_header().resolve()
    chave = parse_key_from_header(cabecalho_chave)
    pacote = caminho_pacote.read_bytes()
    pacote_parseado, _firmware_claro = verificar_pacote_seguro(pacote, chave)

    print('Pacote           : %s' % caminho_pacote)
    print('TrailerVersion   : %d' % pacote_parseado.versao_trailer)
    print('Flags            : 0x%08X' % pacote_parseado.flags)
    print('Firmware         : %d bytes (0x%X)' % (pacote_parseado.tamanho, pacote_parseado.tamanho))
    print('Firmware CRC32   : 0x%08X' % pacote_parseado.crc32_firmware_claro)
    print('Versao           : %d' % pacote_parseado.versao_firmware)
    if pacote_parseado.nonce:
        print('Nonce            : %s' % pacote_parseado.nonce.hex())
    print('AuthTag          : %s' % pacote_parseado.tag_autenticacao.hex())
    print('Chave            : %s' % cabecalho_chave)
