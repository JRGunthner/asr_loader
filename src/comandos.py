import binascii
import os
import pathlib
import struct
from .constantes import EEPROM_ENDERECO_ASR6601CB, EEPROM_ENDERECO_ASR6601SE, EEPROM_SIZE, OTA_MAGIC
from .ota_assinado import build_ota_assinado_package, crc32_ieee, default_key_header, parse_key_from_header, ota_assinado_verify_package
from .utils import get_crc32


def tremo_conectar(processador, lista_portas, baud):
    for porta in reversed(lista_portas):
        print("Serial port %s" % porta)
        try:
            processador.set_port(porta)
            processador.conectar()
            processador.set_baudrate(baud)
            return True
        except Exception as excessao:
            print("Nao foi possivel conectar em %s: %s" % (porta, excessao))
    return False


def tremo_erase(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.erase(param.address, param.size)
    processador.sw_reset(0)


def apagar_eeprom(processador, mostrar_erros=True):
    enderecos_eeprom = (
        ("ASR6601CB", EEPROM_ENDERECO_ASR6601CB),
        ("ASR6601SE", EEPROM_ENDERECO_ASR6601SE),
    )
    variantes_detectadas = []
    falhas = []

    for variante, endereco in enderecos_eeprom:
        try:
            processador.erase(endereco, EEPROM_SIZE)
            variantes_detectadas.append(variante)
        except Exception as excessao:
            if mostrar_erros:
                print('Aviso: nao foi possivel apagar EEPROM para %s em %s: %s' % (variante, hex(endereco), excessao))
            falhas.append((variante, excessao))

    if len(falhas) == len(enderecos_eeprom):
        raise Exception('ERROR: falha ao apagar EEPROM em todos os mapeamentos testados')

    if len(variantes_detectadas) == 1:
        print('Dispositivo identificado: %s' % variantes_detectadas[0])
    elif len(variantes_detectadas) > 1:
        print('Dispositivo identificado: %s' % variantes_detectadas[1])


def tremo_clean_eeprom(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    apagar_eeprom(processador)
    processador.sw_reset(0)


def tremo_flash(param, processador, config):
    if len(param.addr_file) % 2 != 0:
        raise Exception('ERROR: informe pares <address> <filename>')

    arquivos = []
    for i in range(0, len(param.addr_file), 2):
        try:
            endereco = int(param.addr_file[i], 0)
        except Exception:
            raise Exception('ERROR: o endereco "%s" deve ser um numero' % param.addr_file[i])

        arquivo = param.addr_file[i + 1]
        if not os.access(arquivo, os.R_OK):
            raise Exception('ERROR: falha na leitura do arquivo: %s' % arquivo)
        arquivos.append((endereco, arquivo))

    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return False

    if config.apaga_eeprom:
        apagar_eeprom(processador, mostrar_erros=False)

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


def tremo_escrever_otp(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_otp(param.address, binascii.unhexlify(param.data))


def tremo_ler_otp(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.ler_otp(param.address, param.size)


def tremo_escrever_opt0(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_opt0(param.opt0_l, param.opt0_h)


def tremo_ler_opt0(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt0()


def tremo_escrever_opt1(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_opt1(param.opt1_l, param.opt1_h)


def tremo_ler_opt1(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return 0, 0
    return processador.ler_opt1()


def tremo_serial_asr(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.serial_asr()


def tremo_sw_reset(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''
    return processador.sw_reset(0)


def tremo_verify(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return

    image_checksum = get_crc32(param.filename)
    image_size = os.path.getsize(param.filename)

    print('Verificando %s no endereco %s...' % (param.filename, hex(param.address)))
    processador.verify(param.address, image_size, image_checksum)


def tremo_versao_bootloader(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return (0,)
    return processador.versao_bootloader()


def tremo_ler_reg(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return (0,)
    return processador.ler_reg(param.address)


def _formatar_hexdump(endereco_inicial, dados):
    linhas = []
    for offset in range(0, len(dados), 16):
        bloco = dados[offset:offset + 16]
        hex_bytes = ' '.join('%02X' % byte for byte in bloco)
        hex_bytes = hex_bytes.ljust(16 * 3 - 1)
        ascii_bytes = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in bloco)
        linhas.append('%08X  %s  |%s|' % (endereco_inicial + offset, hex_bytes, ascii_bytes))
    return '\n'.join(linhas)


def tremo_ler_mem(param, processador, config):
    if param.size <= 0:
        raise Exception('ERROR: o tamanho deve ser maior que zero')

    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return b''

    endereco_inicial = param.address
    endereco_alinhado = endereco_inicial & ~0x3
    deslocamento_inicial = endereco_inicial - endereco_alinhado
    tamanho_total = deslocamento_inicial + param.size
    quantidade_palavras = (tamanho_total + 3) // 4

    dados_lidos = bytearray()
    for indice in range(quantidade_palavras):
        endereco_atual = endereco_alinhado + (indice * 4)
        valor = processador.ler_reg(endereco_atual)[0]
        dados_lidos.extend(struct.pack('<I', valor))

    dados = bytes(dados_lidos[deslocamento_inicial:deslocamento_inicial + param.size])

    print('Leitura de memoria concluida: %d bytes a partir de %s' % (param.size, hex(endereco_inicial)))
    print(_formatar_hexdump(endereco_inicial, dados))

    if getattr(param, 'output', None):
        with open(param.output, 'wb') as arquivo:
            arquivo.write(dados)
        print('Dump salvo em: %s' % param.output)

    return dados


def tremo_escrever_reg(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.escrever_reg(param.address, param.value)


def tremo_jump(param, processador, config):
    if not tremo_conectar(processador, config.portas_disponiveis, param.baud):
        return
    processador.jump(param.address)


def tremo_ota_pack(param):
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

    with open(out_path, 'wb') as arquivo:
        arquivo.write(header)
        arquivo.write(fw_data)

    print('Firmware : %s' % fw_path)
    print('Tamanho  : %d bytes (0x%X)' % (fw_size, fw_size))
    print('CRC32    : 0x%08X' % fw_crc)
    print('Saida    : %s  (%d bytes no total)' % (out_path, len(header) + fw_size))
    print('Grave o arquivo de saida a partir do endereco 0x00000000 da flash externa.')


def tremo_ota_pack_verify(param):
    caminho_pacote = param.input
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
        raise Exception('ERROR: campo reserved invalido: 0x%08X' % reservado)

    tamanho_esperado = 16 + fw_size
    if len(pacote) != tamanho_esperado:
        raise Exception('ERROR: tamanho total invalido: esperado %d, encontrado %d' % (tamanho_esperado, len(pacote)))

    firmware = pacote[16:]
    crc_calculado = binascii.crc32(firmware) & 0xFFFFFFFF
    if crc_calculado != fw_crc:
        raise Exception('ERROR: CRC32 do firmware invalido: esperado 0x%08X, calculado 0x%08X' % (fw_crc, crc_calculado))

    print('Pacote    : %s' % caminho_pacote)
    print('Magic     : 0x%08X' % magic)
    print('Tamanho   : %d bytes (0x%X)' % (fw_size, fw_size))
    print('CRC32     : 0x%08X' % fw_crc)
    print('Reservado : 0x%08X' % reservado)


def tremo_ota_assinado(param):
    fw_path = param.firmware
    if not os.path.isfile(fw_path):
        raise Exception('ERROR: arquivo nao encontrado: %s' % fw_path)

    if param.output is None:
        base, ext = os.path.splitext(fw_path)
        out_path = '%s_ota_assinado%s' % (base, ext)
    else:
        out_path = param.output

    key_header = pathlib.Path(param.key_header).resolve() if param.key_header is not None else default_key_header().resolve()
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


def tremo_ota_assinado_verify(param):
    package_path = param.input
    if not os.path.isfile(package_path):
        raise Exception('ERROR: arquivo nao encontrado: %s' % package_path)

    key_header = pathlib.Path(param.key_header).resolve() if param.key_header is not None else default_key_header().resolve()
    key = parse_key_from_header(key_header)

    with open(package_path, 'rb') as arquivo:
        package = arquivo.read()

    size, version, auth_tag = ota_assinado_verify_package(package, key)

    print('Pacote   : %s' % package_path)
    print('Firmware : %d bytes (0x%X)' % (size, size))
    print('Versao   : %d' % version)
    print('AuthTag  : %s' % auth_tag.hex())
    print('Chave    : %s' % key_header)
