"""Provisionamento da EEPROM e gravação de produção na mesma sessão serial."""

import hashlib
import hmac
import json
import os
import re
import struct
import zlib
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .exceptions import CmdExcessao

FORMATO = 1
from .rodape_bin import RODAPE, TCHE, separar_rodape

APP_INICIO = 0x08002000
UNIDADE_OTP = 8
TAMANHO_REGISTRO = 96
OFFSET_CHAVE = 8
OFFSET_MARCADOR = 88
MARCADOR = b'CONFOTP1'
APAGADO = b'\xff' * TAMANHO_REGISTRO
FLASH_INICIO = 0x08000000
EEPROM_INICIO = {'ASR6601CB': 0x0801E000, 'ASR6601SE': 0x0803E000}
SRAM_FIM = {'ASR6601CB': 0x20004000, 'ASR6601SE': 0x20010000}
DADOS_MCU = {'ASR6601CB': (1, 128, 16), 'ASR6601SE': (2, 256, 64)}
OTP_INICIO = 0x10001C00
OTP_FIM = 0x10002000
OTP_EEPROM_PR439V3 = 0x10001C00
LIMITE_FLASH_CB = 0x08020000
PAGINA_TESTE_FLASH = 0x08022000
TAMANHO_PAGINA_FLASH = 4096
PADRAO_TESTE_FLASH = b'ASRTEST1'


def _conectar_para_diagnostico(param, processador):
    processador.set_port(param.port)
    processador.conectar()
    processador.set_baudrate(param.baud)
    serial = processador.serial_asr()
    if len(serial) != 8 or serial in (bytes(8), APAGADO[:8]):
        raise ValueError
    return serial


def diagnosticar_flash_asr(param, processador):
    if not param.port:
        raise CmdExcessao('Informe a porta serial com -p para diagnosticar a flash')
    serial_teste: str | None = getattr(param, 'testar_escrita', None)

    if serial_teste is not None and not re.fullmatch(r'[0-9a-fA-F]{16}', serial_teste):
        raise CmdExcessao('--testar-escrita exige o número de série ASR de 8 bytes')

    processador.sessao_reservada = True

    try:
        serial = _conectar_para_diagnostico(param, processador)
        if serial_teste is not None:
            if serial != bytes.fromhex(serial_teste):
                raise CmdExcessao('Número de série diferente da unidade de teste esperada')
            _ensaiar_escrita_flash(processador, serial)
            return

        # Compare palavras separadas por 128 KiB para observar um possível
        # espelhamento, sem enviar comandos de programação ou apagar páginas.
        offsets = (0, 4, 8, 0x100, 0x1000)
        inferior = [processador.ler_reg(FLASH_INICIO + offset)[0] for offset in offsets]

        try:
            superior = [processador.ler_reg(LIMITE_FLASH_CB + offset)[0] for offset in offsets]
        except CmdExcessao:
            superior = None

        if processador.serial_asr() != serial:
            raise ValueError
    except CmdExcessao:
        raise
    except Exception:
        raise CmdExcessao('Falha de comunicação ou identificação na sondagem da flash') from None
    else:
        if superior is None:
            resultado = 'leitura acima de 128 KiB falhou'
        elif superior == inferior:
            resultado = 'leituras iguais nas duas janelas'
        elif superior == [0xFFFFFFFF] * len(offsets):
            resultado = 'janela acima de 128 KiB retornou apenas FF'
        else:
            resultado = 'leituras distintas entre as duas janelas'
        print(f'ASR {serial.hex()}. Sondagem da flash: {resultado}. Variante não confirmada.')
    finally:
        if processador.ser is not None:
            try:
                processador.ser.close()
            except OSError:
                pass
            processador.ser = None


def _ensaiar_escrita_flash(processador, serial):
    pagina_superior = PAGINA_TESTE_FLASH
    pagina_inferior = pagina_superior - (LIMITE_FLASH_CB - FLASH_INICIO)
    crc_apagada = zlib.crc32(b'\xff' * TAMANHO_PAGINA_FLASH)

    try:
        for endereco in (pagina_inferior, pagina_superior):
            processador.verify(endereco, TAMANHO_PAGINA_FLASH, crc_apagada)
    except Exception:
        raise CmdExcessao('Ensaio interrompido antes da escrita. Páginas apagadas não confirmadas') from None

    try:
        processador.flash(pagina_superior, PADRAO_TESTE_FLASH)
        processador.verify(pagina_superior, len(PADRAO_TESTE_FLASH), zlib.crc32(PADRAO_TESTE_FLASH))
        processador.verify(pagina_inferior, TAMANHO_PAGINA_FLASH, crc_apagada)
    except Exception:
        raise CmdExcessao(
            'Ensaio inconclusivo após tentativa de escrita. Verifique a flash da unidade de teste'
        ) from None

    try:
        processador.erase(pagina_superior, TAMANHO_PAGINA_FLASH)
        for endereco in (pagina_inferior, pagina_superior):
            processador.verify(endereco, TAMANHO_PAGINA_FLASH, crc_apagada)
    except Exception:
        raise CmdExcessao('Escrita confirmada. Falha ao restaurar ou verificar as páginas de teste') from None

    print(f'ASR {serial.hex()}. Escrita independente acima de 128 KiB confirmada, compatível com ASR6601SE.')


def diagnosticar_otp(param, processador):
    if not param.port:
        raise CmdExcessao('Informe a porta serial com -p para diagnosticar a OTP')
    processador.sessao_reservada = True

    try:
        serial = _conectar_para_diagnostico(param, processador)
        blocos = [processador.ler_otp(endereco, 512)
                  for endereco in range(OTP_INICIO, OTP_FIM, 512)]

        if any(len(bloco) != 512 for bloco in blocos):
            raise ValueError
    except Exception:
        raise CmdExcessao('Falha ao identificar o equipamento ou ler toda a OTP') from None
    else:
        memoria = b''.join(blocos)
        apagada = b'\xff' * UNIDADE_OTP
        inicio = 0
        faixas = []
        for offset in range(0, len(memoria) + UNIDADE_OTP, UNIDADE_OTP):
            if memoria[offset:offset + UNIDADE_OTP] == apagada:
                continue
            if offset - inicio >= TAMANHO_REGISTRO:
                faixas.append((OTP_INICIO + inicio, OTP_INICIO + offset - 1))
            inicio = offset + UNIDADE_OTP

        print(f'ASR {serial.hex()}. Faixas candidatas com leitura FF:')

        for primeiro, ultimo in faixas:
            print(f'0x{primeiro:08X}–0x{ultimo:08X} ({ultimo - primeiro + 1} bytes)')
        if not faixas:
            print('Nenhuma faixa candidata de 96 bytes alinhados.')
        print('A reserva da faixa requer aprovação da fabricação.')
    finally:
        if processador.ser is not None:
            try:
                processador.ser.close()
            except OSError:
                pass
            processador.ser = None


def _ler_json(caminho, rotulo):
    try:
        dados = json.loads(Path(caminho).read_text(encoding='utf-8'))
        if not isinstance(dados, dict):
            raise ValueError
    except (OSError, ValueError, TypeError):
        raise CmdExcessao(f'{rotulo} ausente ou inválido') from None
    return dados


def _chave_aceitavel(chave):
    return len(chave) == 32 and chave not in (bytes(32), APAGADO[:32])


def _ler_chave(caminho):
    try:
        texto = Path(caminho).read_bytes().strip()
        if not re.fullmatch(rb'[0-9a-fA-F]{64}', texto):
            raise ValueError
        chave = bytes.fromhex(texto.decode('ascii'))
        if not _chave_aceitavel(chave):
            raise ValueError
    except (OSError, ValueError, TypeError):
        raise CmdExcessao('Arquivo da chave EEPROM ausente ou inválido') from None
    return chave


def _versao_valida(versao):
    return type(versao) is int and 0 <= versao <= 9999


def _integridade(corpo):
    crc = zlib.crc32(corpo)
    return struct.pack('<II', crc, crc ^ 0xFFFFFFFF)


def montar_registro(chave, versao, mcu, data):
    _, flash_kib, ram_kib = DADOS_MCU[mcu]
    cabecalho = struct.pack('<BBH4s', FORMATO, TAMANHO_REGISTRO, int(str(versao), 16), b'EEPR')
    modelo = mcu.encode('ascii').ljust(16, b'\0')
    data_local = data.astimezone(ZoneInfo('America/Sao_Paulo')).replace(tzinfo=None)
    data_ascii = data_local.isoformat(timespec='seconds').encode('ascii') + b'\0'
    corpo = cabecalho + chave + modelo + struct.pack('<HH', flash_kib, ram_kib) + data_ascii
    return corpo + _integridade(corpo) + MARCADOR


def classificar_registro(registro):
    if registro == APAGADO:
        return 'VAZIO', None

    if (len(registro) == TAMANHO_REGISTRO
        and registro[:2] == bytes((FORMATO, TAMANHO_REGISTRO))
        and registro[4:8] == b'EEPR'
        and registro[OFFSET_MARCADOR:] == MARCADOR
        and _chave_aceitavel(registro[OFFSET_CHAVE:40])
        and hmac.compare_digest(registro[80:88], _integridade(registro[:80]))):

        try:
            modelo = registro[40:56].rstrip(b'\0').decode('ascii')
            _, flash_kib, ram_kib = DADOS_MCU[modelo]

            if struct.unpack_from('<HH', registro, 56) != (flash_kib, ram_kib):
                raise ValueError
            data = registro[60:80].decode('ascii')

            if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[Z\x00]', data):
                raise ValueError

            datetime.fromisoformat(data[:-1])
            digitos = f"{struct.unpack_from('<H', registro, 2)[0]:04x}"

            return 'VÁLIDO', int(digitos, 10)
        except (KeyError, ValueError):
            pass
    return 'INVÁLIDO/INCOMPLETO', None


def ler_binario_producao(caminho, mcu):
    try:
        limite = EEPROM_INICIO[mcu] - FLASH_INICIO

        with Path(caminho).open('rb') as arquivo:
            pacote = arquivo.read(limite + RODAPE.size + len(TCHE) + 1)
        imagem, dados = separar_rodape(pacote)

        if (dados is None or dados['tipo'] not in (0, 1)
            or not APP_INICIO - FLASH_INICIO + 8 <= len(imagem) <= limite
            or dados['mcu'] != DADOS_MCU[mcu][0] or dados['otp'] != OTP_EEPROM_PR439V3
            or dados['formato_otp'] != FORMATO or dados['origem'] != FLASH_INICIO
            or dados['aplicacao'] != APP_INICIO):
            raise ValueError

        for inicio, fim in ((FLASH_INICIO, APP_INICIO), (APP_INICIO, FLASH_INICIO + len(imagem))):
            pilha, entrada = struct.unpack_from('<II', imagem, inicio - FLASH_INICIO)
            if (not 0x20000000 < pilha <= SRAM_FIM[mcu] or pilha % 8 or not entrada & 1
                or not inicio <= (entrada & ~1) < fim):
                raise ValueError
    except (OSError, KeyError, ValueError, struct.error):
        raise CmdExcessao('Binário de produção inválido, divergente ou incompatível') from None
    return imagem, dados['versao']


def preparar_producao(param):
    if not param.port:
        raise CmdExcessao('Produção exige porta explícita com -p')

    if param.serial_producao is not None and not re.fullmatch(r'[0-9A-Fa-f]{16}', param.serial_producao):
        raise CmdExcessao('--serial-producao exige 16 dígitos hexadecimais')

    binario = getattr(param, 'producao_bin', False)
    base = OTP_EEPROM_PR439V3
    mcu = param.mcu

    if mcu not in EEPROM_INICIO:
        raise CmdExcessao('Informe --mcu com a variante conferida no equipamento')

    if binario:
        try:
            endereco, caminho = param.addr_file
            if int(endereco, 0) != FLASH_INICIO:
                raise ValueError
        except (ValueError, TypeError):
            raise CmdExcessao('Informe o endereço de flash 0x08000000 e um único binário de produção') from None
        firmware, versao = ler_binario_producao(caminho, mcu)
    else:
        manifesto = _ler_json(param.producao, 'Manifesto de produção')
        try:
            versao = manifesto['versao']
            if (manifesto['mcu'] != mcu or manifesto['otp_formato'] != FORMATO
                or int(manifesto['otp_base'], 0) != base or not _versao_valida(versao)):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise CmdExcessao('Firmware incompatível com a variante ou a reserva OTP do PR439v3') from None

        try:
            endereco, caminho = param.addr_file
            if int(endereco, 0) != FLASH_INICIO:
                raise ValueError
            limite = EEPROM_INICIO[mcu] - FLASH_INICIO

            with Path(caminho).open('rb') as arquivo:
                firmware = arquivo.read(limite + 1)

            if not 8 <= len(firmware) <= limite:
                raise ValueError

            pilha, entrada = struct.unpack_from('<II', firmware)
            if (not 0x20000000 < pilha <= SRAM_FIM[mcu] or pilha % 8 or not entrada & 1
                or not FLASH_INICIO <= (entrada & ~1) < FLASH_INICIO + len(firmware)):
                raise ValueError

            if (separar_rodape(firmware)[1] is not None
                or manifesto['sha256'] != hashlib.sha256(firmware).hexdigest()):
                raise ValueError
        except (KeyError, OSError, TypeError, ValueError):
            raise CmdExcessao('Binário de produção inválido, divergente ou fora da faixa de flash') from None

    return base, versao, firmware, _ler_chave_producao(), mcu


def _ler_chave_producao():
    caminho_chave = os.environ.get('ASR_ARQUIVO_CHAVE_EEPROM')
    if not caminho_chave:
        raise CmdExcessao('Configure ASR_ARQUIVO_CHAVE_EEPROM com o caminho do arquivo da chave')
    return _ler_chave(caminho_chave)


def mostrar_previa_otp_producao(caminho, mcu, exibir_chave=False):
    _, versao = ler_binario_producao(caminho, mcu)
    registro = montar_registro(_ler_chave_producao(), versao, mcu, datetime.now(timezone.utc))
    flash_kib, ram_kib = struct.unpack_from('<HH', registro, 56)
    crc, complemento_crc = struct.unpack_from('<II', registro, 80)

    campos = (
        (0x00, 1, 'Formato', str(registro[0])),
        (0x01, 1, 'Tamanho total', f'{registro[1]} bytes'),
        (0x02, 2, 'Versão inicial (BCD)', f'{versao:04d}'),
        (0x04, 4, 'Identificador', registro[4:8].decode('ascii')),
        (OFFSET_CHAVE, 32, 'chave da EEPROM', 'visível no pacote' if exibir_chave else 'oculta'),
        (0x28, 16, 'Modelo', mcu),
        (0x38, 2, 'Flash', f'{flash_kib} KiB'),
        (0x3A, 2, 'RAM', f'{ram_kib} KiB'),
        (0x3C, 20, 'Data e hora', registro[60:79].decode('ascii')),
        (0x50, 4, 'CRC32', f'0x{crc:08X}'),
        (0x54, 4, 'Complemento do CRC32', f'0x{complemento_crc:08X}'),
        (OFFSET_MARCADOR, 8, 'Marcador', registro[OFFSET_MARCADOR:].decode('ascii')),
    )

    base = OTP_EEPROM_PR439V3
    print(f'Prévia OTP de produção para uma OTP vazia (0x{base:08X}–0x{base + len(registro) - 1:08X})')
    print('A data e hora e o CRC serão recalculados na gravação.')
    print()
    print(f'{"Offset":<8} {"Bytes":>5}  {"Campo":<22} Valor')

    for offset, tamanho, campo, valor in campos:
        print(f'0x{offset:02X}     {tamanho:>5}  {campo:<22} {valor}')

    print()
    print('Pacote OTP em hexadecimal' + ('' if exibir_chave else ' (XX indica byte de chave oculto)'))

    for offset in range(0, len(registro), UNIDADE_OTP):
        bloco = registro[offset:offset + UNIDADE_OTP]
        octetos = (
            'XX' if not exibir_chave and OFFSET_CHAVE <= posicao < OFFSET_CHAVE + 32 else f'{byte:02X}'
            for posicao, byte in enumerate(bloco, offset)
        )
        print(f'0x{base + offset:08X}  {" ".join(octetos)}')


def _ler_registro_otp(processador, base):
    try:
        registro = processador.ler_otp(base, TAMANHO_REGISTRO)
        if len(registro) != TAMANHO_REGISTRO:
            raise ValueError
    except Exception:
        raise CmdExcessao('Falha de comunicação na leitura inicial da OTP') from None
    return registro


def _validar_registro_otp(registro, chave, mcu):
    estado, inicial = classificar_registro(registro)
    if estado == 'VÁLIDO':
        if not hmac.compare_digest(registro[OFFSET_CHAVE:40], chave):
            raise CmdExcessao('Incompatibilidade com a chave da EEPROM configurada')
        if registro[40:56].rstrip(b'\0') != mcu.encode('ascii'):
            raise CmdExcessao('Variante registrada difere da variante informada')
    return estado, inicial


def ler_estado_otp(processador, base, chave, mcu):
    return _validar_registro_otp(_ler_registro_otp(processador, base), chave, mcu)


def _resumir_metadados_otp(registro):
    modelo = registro[40:56].rstrip(b'\0').decode('ascii')
    flash_kib, ram_kib = struct.unpack_from('<HH', registro, 56)
    data = registro[60:80].rstrip(b'\0').decode('ascii')
    fuso = 'UTC' if data.endswith('Z') else 'São Paulo'
    return (f'quadro v{registro[0]}, {modelo}, flash {flash_kib} KiB, RAM {ram_kib} KiB, '
            f'provisionada em {data} ({fuso})')


def inspecionar_otp_para_gravacao(processador, mcu):
    """Consulta a OTP na mesma sessão e devolve um resumo sem expor a chave."""
    try:
        registro = _ler_registro_otp(processador, OTP_EEPROM_PR439V3)
    except CmdExcessao as falha:
        return f'OTP NÃO VERIFICADA — {falha}'

    estado, _ = classificar_registro(registro)
    if estado != 'VÁLIDO':
        return f'OTP {estado}'

    try:
        chave = _ler_chave_producao()
    except CmdExcessao as falha:
        return f'OTP NÃO VERIFICADA — {falha}'

    try:
        _validar_registro_otp(registro, chave, mcu)
    except CmdExcessao as falha:
        return f'OTP INCOMPATÍVEL — {falha}'

    return 'OTP VÁLIDO'


def provisionar(processador, base, chave, versao, mcu):
    registro = _ler_registro_otp(processador, base)
    estado, inicial = _validar_registro_otp(registro, chave, mcu)

    if estado == 'INVÁLIDO/INCOMPLETO':
        raise CmdExcessao('Registro OTP inválido ou incompleto')

    if estado == 'VÁLIDO':
        return inicial, 'preservado', registro

    esperado = montar_registro(chave, versao, mcu, datetime.now(timezone.utc))
    offsets = range(0, OFFSET_MARCADOR, UNIDADE_OTP)
    try:
        for offset in offsets:
            unidade = esperado[offset:offset + UNIDADE_OTP]
            if unidade != APAGADO[:UNIDADE_OTP]:
                processador.escrever_otp(base + offset, unidade)

        corpo = processador.ler_otp(base, TAMANHO_REGISTRO)
        if not hmac.compare_digest(corpo, esperado[:OFFSET_MARCADOR] + APAGADO[:8]):
            raise ValueError

        processador.escrever_otp(base + OFFSET_MARCADOR, MARCADOR)
        confirmado = processador.ler_otp(base, TAMANHO_REGISTRO)
        if not hmac.compare_digest(confirmado, esperado):
            raise ValueError
    except Exception:
        raise CmdExcessao('Falha ao programar ou confirmar o registro OTP. Operação interrompida') from None
    return versao, 'provisionado', confirmado


def gravar_producao(param, processador, config):
    base, versao, firmware, chave, mcu = preparar_producao(param)
    processador.sessao_reservada = True

    try:
        try:
            processador.set_port(param.port)
            processador.conectar()
            processador.set_baudrate(param.baud)
            serial_lido = processador.serial_asr()
        except Exception:
            raise CmdExcessao('Falha ao conectar ou identificar o equipamento') from None

        if len(serial_lido) != 8 or serial_lido in (bytes(8), APAGADO[:8]):
            raise CmdExcessao('Número de série ASR inválido')

        if param.serial_producao is not None and serial_lido != bytes.fromhex(param.serial_producao):
            raise CmdExcessao('Número de série ASR diferente do equipamento esperado')

        def registrar(res):
            mensagem = f'Produção ASR {serial_lido.hex()} — {res}'
            print(mensagem)
            config.log(mensagem)

        try:
            if getattr(param, 'somente_validar', False):
                estado, inicial = ler_estado_otp(processador, base, chave, mcu)
                resumo = f'OTP {estado}'

                if inicial is not None:
                    resumo += f', versão inicial {inicial}'

                if estado == 'INVÁLIDO/INCOMPLETO':
                    raise CmdExcessao(resumo)

                registrar(resumo)
                return False
            inicial, resultado, registro = provisionar(processador, base, chave, versao, mcu)
        except CmdExcessao as falha:
            registrar(str(falha))
            raise
        try:
            # ERASE pode arredondar para uma página de 4 KiB. O limite da
            # imagem foi verificado numa fronteira de página antes da conexão.
            processador.erase(FLASH_INICIO, len(firmware))

            for offset in range(0, len(firmware), 512):
                processador.flash(FLASH_INICIO + offset, firmware[offset:offset + 512])
            processador.verify(FLASH_INICIO, len(firmware), zlib.crc32(firmware))
        except Exception:
            raise CmdExcessao('OTP confirmada. Falha ao gravar ou verificar o firmware') from None
        finally:
            registrar(f'OTP {resultado}, versão inicial {inicial}, {_resumir_metadados_otp(registro)}')
        registrar(f'firmware gravado e verificado, versão {versao}')

        try:
            processador.sw_reset(0)
        except Exception:
            raise CmdExcessao('Firmware verificado. Falha ao reiniciar o equipamento') from None
        return True
    finally:
        if processador.ser is not None:
            try:
                processador.ser.close()
            except OSError:
                pass
            processador.ser = None
