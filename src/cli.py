import argparse
import platform
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, cast

import serial

from .ASRLoader import ASRLoader as ASRLoader
from .comandos import *
from .constantes import BAUD_DEFAULT, TIMEOUT_DEFAULT, VERSAO_GRAVADOR
from .runtime import RuntimeConfig
from .producao import diagnosticar_flash_asr, diagnosticar_otp, ler_binario_producao, mostrar_previa_otp_producao
from .rodape_bin import acrescentar_rodape, formatar_tabela_rodape, separar_rodape
from .utils import arg_int, get_lista_portas_com, get_lista_portas_info


class Comandos(str, Enum):
    MAKE = 'make'
    ERASE = 'erase'
    FLASH = 'flash'
    VERIFY = 'verify'
    RESET = 'reset'
    HW_RESET = 'hw_reset'
    CLEAR_EEPROM = 'clear_eeprom'
    IDENTIFICAR_MCU = 'identificar_mcu'
    MAPA_FLASH = 'mapa_flash'
    MAPA_SRAM = 'mapa_sram'
    MAPA_EEPROM = 'mapa_eeprom'
    MAPA_MEMORIA = 'mapa_memoria'
    SERIAL = 'serial'

    DTR1 = 'dtr1'
    DTR0 = 'dtr0'
    RTS1 = 'rts1'
    RTS0 = 'rts0'

    COMDIAG = 'comdiag'
    TESTEBOOT = 'testeboot'
    DOCTOR = 'doctor'
    PREVALIDAR = 'prevalidar'
    FIRMWARE_INSPECT = 'firmware_inspect'
    SNAPSHOT = 'snapshot'

    OTA_PACK = 'ota_pack'
    OTA_PACK_VERIFY = 'ota_pack_verify'
    OTA_PACK_INSPECT = 'ota_pack_inspect'
    OTA_CRIPT = 'ota_cript'
    OTA_CRIPT_VERIFY = 'ota_cript_verify'

    JUMP = 'jump'

    VERSAO_BOOTLOADER = 'versao_bootloader'

    LER_OTP = 'ler_otp'
    DIAGNOSTICAR_OTP = 'diagnosticar_otp'
    DIAGNOSTICAR_FLASH_ASR = 'diagnosticar_flash_asr'
    ESCREVER_OTP = 'escrever_otp'

    LER_OPT0 = 'ler_opt0'
    ESCREVER_OPT0 = 'escrever_opt0'

    LER_OPT1 = 'ler_opt1'
    ESCREVER_OPT1 = 'escrever_opt1'

    LER_REG = 'ler_reg'
    ESCREVER_REG = 'escrever_reg'
    LER_MEM = 'ler_mem'

    VERSAO = 'versao'
    HELP = 'help'


class Argumentos(str, Enum):
    ADDRESS = 'address'
    SIZE = 'size'
    DATA = 'data'
    VALUE = 'value'
    FILENAME = 'filename'
    FIRMWARE = 'firmware'
    HOLD = 'hold'
    OUTPUT = 'output'
    INPUT = 'input'
    OPT0_L = 'opt0_l'
    OPT0_H = 'opt0_h'
    OPT1_L = 'opt1_l'
    OPT1_H = 'opt1_h'
    ADDR_FILE = 'addr_file'
    KEY_HEADER = 'key_header'
    FIRMWARE_VERSION = 'firmware_version'
    JSON = 'json'
    LOG_FILE = 'log_file'
    TRACE_JSON = 'trace_json'
    BASE_ADDRESS = 'base_address'
    PROFILE = 'profile'
    STRICT = 'strict'
    STRICT_APP_RANGE = 'strict_app_range'
    SWEEP = 'sweep'
    SWEEP_BAUDS = 'sweep_bauds'
    SWEEP_RESET_DELAYS = 'sweep_reset_delays'
    SWEEP_RELEASE_DELAYS = 'sweep_release_delays'


class Opcoes(Enum):
    PORT = ('--port', '-p', 'porta serial')
    BAUD = ('--baud', '-b', 'baudrate, default 921600')
    VERBOSE = ('--verbose', '-v', 'modo verbose para debug')
    TIMEOUT = ('--timeout', '-t', 'timeout da serial em segundos, default 2s')
    EEPROM = ('--eeprom', '-e', 'mantém os dados da eeprom emulada')

    @property
    def long(self):
        return self.value[0]

    @property
    def short(self):
        return self.value[1]

    @property
    def texto(self):
        return self.value[2]


def cli_printar_help(help_parser):
    print("Tremo Loader v%s" % VERSAO_GRAVADOR)
    help_parser.print_help()
    print("\nPortas seriais disponiveis:")
    portas = get_lista_portas_com()
    if len(portas) == 0:
        print("  Nenhuma porta serial encontrada")
    else:
        for porta in portas:
            print(" ", porta)


def cli_obter_data_build():
    if getattr(sys, 'frozen', False):
        caminho_build = Path(sys.executable)
    else:
        caminho_build = Path(__file__).resolve().parents[1] / 'asr_loader.py'
        if not caminho_build.exists():
            caminho_build = Path(__file__).resolve()

    return caminho_build.stat().st_mtime_ns // 1_000_000_000, caminho_build


def cli_montar_diagnostico():
    timestamp, caminho_build = cli_obter_data_build()
    return {
        'app': 'ASR Loader',
        'version': VERSAO_GRAVADOR,
        'build_date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        'build_source': str(caminho_build),
        'cwd': str(Path.cwd()),
        'python': {
            'version': sys.version.replace('\n', ' '),
            'executable': sys.executable,
            'platform': platform.platform(),
        },
        'pyserial': getattr(serial, '__version__', 'desconhecido'),
        'ports': get_lista_portas_info(),
    }


def cli_printar_diagnostico(args):
    diagnostico = cli_montar_diagnostico()
    if args.json:
        print(json.dumps(diagnostico, indent=2, ensure_ascii=False))
        return

    portas = cast(List[Dict[str, object]], diagnostico['ports'])
    print('%s v%s' % (diagnostico['app'], diagnostico['version']))
    print('Build     : %s' % diagnostico['build_date'])
    print('Fonte     : %s' % diagnostico['build_source'])
    print('Diretorio : %s' % diagnostico['cwd'])
    print('Python    : %s' % diagnostico['python']['version'])
    print('Executavel: %s' % diagnostico['python']['executable'])
    print('Plataforma: %s' % diagnostico['python']['platform'])
    print('pyserial  : %s' % diagnostico['pyserial'])
    print('')
    print('Portas seriais:')
    if not portas:
        print('  Nenhuma porta serial encontrada')
        return

    for porta_info in portas:
        vid_valor = porta_info.get('vid')
        pid_valor = porta_info.get('pid')
        vid = ('0x%04X' % vid_valor) if isinstance(vid_valor, int) else ''
        pid = ('0x%04X' % pid_valor) if isinstance(pid_valor, int) else ''
        vid_pid = '%s/%s' % (vid, pid) if vid or pid else ''
        print('  %s' % porta_info.get('device', ''))
        print('    Descricao : %s' % (porta_info.get('description') or ''))
        print('    HWID      : %s' % (porta_info.get('hwid') or ''))
        print('    VID/PID   : %s' % vid_pid)
        print('    Fabricante: %s' % (porta_info.get('manufacturer') or ''))
        print('    Produto   : %s' % (porta_info.get('product') or ''))


def cli_adicionar_argumentos(argumentos):
    argumentos.add_argument(Opcoes.PORT.long, Opcoes.PORT.short, help=Opcoes.PORT.texto)
    argumentos.add_argument(Opcoes.BAUD.long, Opcoes.BAUD.short, help=Opcoes.BAUD.texto, type=int, default=BAUD_DEFAULT)
    argumentos.add_argument(Opcoes.VERBOSE.long, Opcoes.VERBOSE.short, help=Opcoes.VERBOSE.texto, action='store_true')
    argumentos.add_argument(Opcoes.TIMEOUT.long, Opcoes.TIMEOUT.short, help=Opcoes.TIMEOUT.texto, type=int,
                            default=TIMEOUT_DEFAULT)
    argumentos.add_argument(Opcoes.EEPROM.long, Opcoes.EEPROM.short, help=Opcoes.EEPROM.texto, action='store_true')
    argumentos.add_argument('--v8', help='usar o mapeamento de EEPROM de 1 KiB do firmware v8', action='store_true')
    argumentos.add_argument('--no-auto-boot', help='nao aciona DTR/RTS automaticamente antes de conectar',
                            action='store_true')
    argumentos.add_argument('--boot-reset-delay', help='tempo em segundos mantendo o reset ativo via RTS, default 0.1s',
                            type=float, default=0.1)
    argumentos.add_argument('--boot-release-delay',
                            help='tempo em segundos antes de liberar o modo boot via DTR, default 0.1s',
                            type=float, default=0.1)
    argumentos.add_argument('--log-file', dest=Argumentos.LOG_FILE.value,
                            help='arquivo para salvar diagnostico da execucao e pacotes TX/RX')
    argumentos.add_argument('--trace-json', dest=Argumentos.TRACE_JSON.value,
                            help='arquivo JSON Lines para trace estruturado de comandos e TX/RX')


def cli_adicionar_comando_linha_serial(subparsers, comando, linha, estado):
    parser_linha = subparsers.add_parser(comando, help='seta %s=%d para teste de hardware' % (
        linha.upper(), 1 if estado else 0))
    parser_linha.add_argument('--hold', dest=Argumentos.HOLD.value, type=float,
                              help='tempo em segundos mantendo a porta aberta; sem este parametro, aguarda Ctrl+C')
    parser_linha.set_defaults(control_line=linha, control_state=estado)


def cli_montar_doctor(args, config, processador):
    diagnostico = cli_montar_diagnostico()
    portas_info = cast(List[Dict[str, object]], diagnostico['ports'])
    portas = [str(porta.get('device')) for porta in portas_info if porta.get('device')]
    total_portas = len(portas)
    rotulo_porta = 'porta detectada' if total_portas == 1 else 'portas detectadas'
    checks = [{
        'name': 'pyserial',
        'status': 'pass' if diagnostico['pyserial'] != 'desconhecido' else 'warn',
        'detail': diagnostico['pyserial'],
    }, {
        'name': 'portas_seriais',
        'status': 'pass' if portas else 'fail',
        'detail': '%d %s' % (total_portas, rotulo_porta),
    }]

    if args.port is not None:
        checks.append({
            'name': 'porta_selecionada',
            'status': 'pass' if args.port in portas else 'warn',
            'detail': args.port,
        })
    checks.append({
        'name': 'auto_boot',
        'status': 'pass' if config.auto_boot else 'warn',
        'detail': 'reset=%.3fs release=%.3fs' % (config.boot_reset_delay, config.boot_release_delay),
    })

    if args.testeboot:
        try:
            if args.json:
                with contextlib.redirect_stdout(io.StringIO()):
                    asr_probe(args, processador, config)
            else:
                asr_probe(args, processador, config)
            checks.append({'name': 'testeboot_bootloader', 'status': 'pass', 'detail': 'boot respondeu'})
        except Exception as excessao:
            checks.append({'name': 'testeboot_bootloader', 'status': 'fail', 'detail': str(excessao)})
        finally:
            asr_fechar_porta(processador)

    recomendacoes = []
    if not portas:
        recomendacoes.append('Verifique cabo USB, driver do CP2102 e permissao de acesso a porta serial.')
    if args.port is not None and args.port not in portas:
        recomendacoes.append('A porta informada nao apareceu no diagnostico; confira o nome COMx.')
    if any(item['name'] == 'testeboot_bootloader' and item['status'] == 'fail' for item in checks):
        recomendacoes.append('Rode testeboot --sweep para encontrar delays estaveis de DTR/RTS.')
        recomendacoes.append('Teste dtr1/dtr0/rts1/rts0 medindo primeiro no CP2102 e depois no MCU.')
    if not recomendacoes:
        recomendacoes.append('Ambiente básico consistente; para falhas intermitentes use --trace-json e --log-file.')

    return {
        'diagnostic': diagnostico,
        'config': {
            'baud': args.baud,
            'timeout': args.timeout,
            'auto_boot': config.auto_boot,
            'boot_reset_delay': config.boot_reset_delay,
            'boot_release_delay': config.boot_release_delay,
            'ports': config.portas_disponiveis,
        },
        'checks': checks,
        'recommendations': recomendacoes,
    }


def cli_printar_doctor(relatorio):
    diag = relatorio['diagnostic']
    print('%s v%s' % (diag['app'], diag['version']))
    print('Python   : %s' % diag['python']['version'])
    print('pyserial : %s' % diag['pyserial'])
    print('Portas   : %s' % (', '.join(relatorio['config']['ports']) or '<nenhuma>'))
    print('Checks:')
    for item in relatorio['checks']:
        print('  [%s] %s - %s' % (item['status'].upper(), item['name'], item['detail']))
    print('Recomendações:')
    for item in relatorio['recommendations']:
        print('  - %s' % item)


def cli_build_parser():
    parser = argparse.ArgumentParser()
    cli_adicionar_argumentos(parser)

    msg_help = 'run asr_loader.py {command} -h'
    subparsers = parser.add_subparsers(dest='command', help=msg_help)

    parser_erase = subparsers.add_parser(Comandos.ERASE.value, help='apagar determinada area da flash')
    parser_erase.add_argument(Argumentos.ADDRESS.value, help='endereco da flash a ser apagada', type=arg_int)
    parser_erase.add_argument(Argumentos.SIZE.value, help='quantidade de bytes a serem apagados', type=arg_int)

    parser_flash = subparsers.add_parser(Comandos.FLASH.value, help='apagar e gravar a flash')
    modo_producao = parser_flash.add_mutually_exclusive_group()
    modo_producao.add_argument('--producao', metavar='MANIFESTO', help='gravar produção no formato legado com JSON')
    modo_producao.add_argument('--producao-bin', action='store_true',
                               help='validar metadados e gravar binário de produção')
    modo_producao.add_argument('--relatar-otp', action='store_true',
                               help='conferir a OTP antes de gravar e mostrar o resultado no final')
    parser_flash.add_argument('--mcu', choices=('ASR6601CB', 'ASR6601SE'),
                              help='variante conferida no equipamento')
    parser_flash.add_argument('--eeprom-ab', action='store_true',
                              help='usar as duas páginas da EEPROM do ASR6601SE (exige --mcu ASR6601SE)')
    parser_flash.add_argument('--serial-producao', metavar='SERIAL_HEX',
                              help='conferência opcional do serial lido automaticamente (16 dígitos hex)')
    parser_flash.add_argument('--somente-validar', action='store_true',
                              help='classificar a OTP em modo de produção sem gravar')
    parser_flash.add_argument(Argumentos.ADDR_FILE.value, metavar='<address> <filename>',
                              help='endereco e nome do arquivo, Ex.: 0x08000000 app.bin', nargs='+')

    parser_producao_inspect = subparsers.add_parser('producao_inspect',
                                                    help='validar o binário de produção sem porta serial')
    parser_producao_inspect.add_argument('arquivo')
    parser_producao_inspect.add_argument('--mcu', required=True, choices=('ASR6601CB', 'ASR6601SE'))

    parser_otp_producao = subparsers.add_parser(
        'otp_producao_inspect', help='mostrar a tabela e o pacote OTP de produção sem conectar à placa')
    parser_otp_producao.add_argument('arquivo', help='binário de produção com rodapé ASRPROD')
    parser_otp_producao.add_argument('--mcu', required=True, choices=('ASR6601CB', 'ASR6601SE'))
    parser_otp_producao.add_argument('--exibir-chave', action='store_true',
                                     help='incluir a chave da EEPROM na saída hexadecimal')

    parser_bin_inspect = subparsers.add_parser('bin_inspect', help='validar e exibir os metadados do binário (ASRPROD)')
    parser_bin_inspect.add_argument('arquivo', type=Path)
    parser_bin_extrair = subparsers.add_parser('bin_extrair',
                                               help='extrair o conteúdo gravável ou o pacote OTA original')
    parser_bin_extrair.add_argument('arquivo', type=Path)
    parser_bin_extrair.add_argument('saida', type=Path)
    parser_bin_empacotar = subparsers.add_parser('bin_empacotar', help='acrescentar os metadados aos binários do build')
    parser_bin_empacotar.add_argument('arquivo', type=Path)
    parser_bin_empacotar.add_argument('saida', type=Path)
    for campo in ('versao', 'variante', 'tipo', 'origem', 'aplicacao'):
        parser_bin_empacotar.add_argument(campo, type=arg_int)

    parser_escrever_otp = subparsers.add_parser(Comandos.ESCREVER_OTP.value,
                                                help='escrever em uma area da opt da flash')
    parser_escrever_otp.add_argument(Argumentos.ADDRESS.value, help='endereco flash otp', type=arg_int)
    parser_escrever_otp.add_argument(Argumentos.DATA.value, help='dado a ser escrito na flash (hexadecimal)')

    parser_ler_otp = subparsers.add_parser(Comandos.LER_OTP.value, help='ler a area da otp da flash')
    subparsers.add_parser(Comandos.DIAGNOSTICAR_OTP.value, help='listar faixas candidatas por leitura da OTP')
    parser_diagnosticar_flash = subparsers.add_parser(Comandos.DIAGNOSTICAR_FLASH_ASR.value,
                                                      help='sondar a flash no limite de 128 KiB')
    parser_diagnosticar_flash.add_argument('--testar-escrita', metavar='SERIAL_HEX',
                                           help='ensaiar escrita na flash de uma unidade de bancada')
    parser_ler_otp.add_argument(Argumentos.ADDRESS.value, help='endereco flash otp', type=arg_int)
    parser_ler_otp.add_argument(Argumentos.SIZE.value, help='endereco flash otp', type=arg_int)

    parser_escrever_opt0 = subparsers.add_parser(Comandos.ESCREVER_OPT0.value, help='escrever na area opt0 da flash')
    parser_escrever_opt0.add_argument(Argumentos.OPT0_L.value, help='valor msb a ser escrito', type=arg_int)
    parser_escrever_opt0.add_argument(Argumentos.OPT0_H.value, help='valor lsb a ser escrito', type=arg_int)

    subparsers.add_parser(Comandos.LER_OPT0.value, help='ler a area opt0 da flash')

    parser_escrever_opt1 = subparsers.add_parser(Comandos.ESCREVER_OPT1.value, help='escrever na area opt1 da flash')
    parser_escrever_opt1.add_argument(Argumentos.OPT1_L.value, help='valor msb a ser escrito', type=arg_int)
    parser_escrever_opt1.add_argument(Argumentos.OPT1_H.value, help='valor lsb a ser escrito', type=arg_int)

    subparsers.add_parser(Comandos.LER_OPT1.value, help='ler a area opt1 da flash')
    subparsers.add_parser(Comandos.SERIAL.value, help='ler o serial do ASR')
    subparsers.add_parser(Comandos.IDENTIFICAR_MCU.value,
                          help='identificar ASR6601CB ou ASR6601SE pelo teste de EEPROM do flash')
    for comando, texto in (
            (Comandos.MAPA_FLASH.value, 'ler o mapa e os bytes da flash interna do MCU conectado'),
            (Comandos.MAPA_SRAM.value, 'ler o mapa e os bytes da SRAM do MCU conectado'),
            (Comandos.MAPA_EEPROM.value, 'ler o mapa e os bytes da EEPROM emulada do MCU conectado')):
        parser_mapa = subparsers.add_parser(comando, help=texto)
        parser_mapa.add_argument(Argumentos.OUTPUT.value, nargs='?', help='arquivo binario opcional para salvar o dump')
        parser_mapa.add_argument('--mcu', choices=('cb', 'se'),
                                 help='modelo conhecido; evita a identificacao por apagamento da EEPROM')
        if comando == Comandos.MAPA_EEPROM.value:
            modo_eeprom = parser_mapa.add_mutually_exclusive_group()
            modo_eeprom.add_argument('--eeprom-ab', action='store_true',
                                     help='ler as duas páginas da EEPROM do ASR6601SE (exige --mcu se)')
            modo_eeprom.add_argument('--eeprom-ativa', action='store_true',
                                     help='exportar uma página bruta, escolhida pelo cabeçalho (exige --mcu se)')
    parser_mapa_memoria = subparsers.add_parser(Comandos.MAPA_MEMORIA.value,
                                                help='mostrar o mapa completo de memoria do MCU conectado')
    parser_mapa_memoria.add_argument('--mcu', choices=('cb', 'se'),
                                     help='modelo conhecido; evita a identificacao por apagamento da EEPROM')
    parser_mapa_memoria.add_argument('--eeprom-ab', action='store_true',
                                     help='mostrar as duas páginas da EEPROM do PR439v3 (exige --mcu se)')
    parser_comdiag = subparsers.add_parser(Comandos.COMDIAG.value,
                                           help='mostra diagnostico do ambiente e portas seriais')
    parser_comdiag.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                                help='imprime o diagnostico em JSON')
    parser_doctor = subparsers.add_parser(Comandos.DOCTOR.value,
                                          help='executa diagnostico guiado do ambiente e opcionalmente do bootloader')
    parser_doctor.add_argument('--testeboot', action='store_true',
                               help='tambem tenta sincronizar com o bootloader')
    parser_doctor.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                               help='imprime o diagnostico em JSON')
    parser_probe = subparsers.add_parser(Comandos.TESTEBOOT.value,
                                         help='testa entrada no bootloader e sincronismo sem apagar ou gravar')
    parser_probe.add_argument('--sweep', dest=Argumentos.SWEEP.value, action='store_true',
                              help='testa combinacoes de baudrate e delays de auto boot')
    parser_probe.add_argument('--sweep-bauds', dest=Argumentos.SWEEP_BAUDS.value,
                              default=str(BAUD_DEFAULT),
                              help='bauds separados por virgula, default: %(default)s')
    parser_probe.add_argument('--sweep-reset-delays', dest=Argumentos.SWEEP_RESET_DELAYS.value,
                              default='0.05,0.1,0.2',
                              help='delays de reset separados por virgula, em segundos')
    parser_probe.add_argument('--sweep-release-delays', dest=Argumentos.SWEEP_RELEASE_DELAYS.value,
                              default='0.05,0.1,0.2',
                              help='delays de release separados por virgula, em segundos')
    parser_probe.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                              help='imprime resultado do sweep em JSON')
    subparsers.add_parser(Comandos.RESET.value, help='resetar o ASR')
    parser_hw_reset = subparsers.add_parser(Comandos.HW_RESET.value,
                                            help='resetar o ASR via linha RTS sem conectar no bootloader')
    parser_hw_reset.add_argument('--boot', help='mantem DTR ativo durante o reset para entrar no bootloader',
                                 action='store_true')
    cli_adicionar_comando_linha_serial(subparsers, Comandos.DTR1.value, 'dtr', True)
    cli_adicionar_comando_linha_serial(subparsers, Comandos.DTR0.value, 'dtr', False)
    cli_adicionar_comando_linha_serial(subparsers, Comandos.RTS1.value, 'rts', True)
    cli_adicionar_comando_linha_serial(subparsers, Comandos.RTS0.value, 'rts', False)

    parser_verify = subparsers.add_parser(Comandos.VERIFY.value, help='verificar o conteudo da flash')
    parser_verify.add_argument(Argumentos.ADDRESS.value, help='endereco da flash a ser verificado', type=arg_int)
    parser_verify.add_argument(Argumentos.FILENAME.value, help='arquivo para comparar com a flash')

    subparsers.add_parser(Comandos.VERSAO_BOOTLOADER.value,
                          help='ler o version number bruto retornado pelo comando VERSION do bootloader')

    parser_ler_reg = subparsers.add_parser(Comandos.LER_REG.value, help='ler o conteudo de um registrador')
    parser_ler_reg.add_argument(Argumentos.ADDRESS.value, help='endereco do registrador a ser lido', type=arg_int)

    parser_ler_mem = subparsers.add_parser(Comandos.LER_MEM.value,
                                           help='ler uma regiao de memoria em palavras de 32 bits')
    parser_ler_mem.add_argument(Argumentos.ADDRESS.value, help='endereco inicial da memoria a ser lida', type=arg_int)
    parser_ler_mem.add_argument(Argumentos.SIZE.value, help='quantidade de bytes a serem lidos', type=arg_int)
    parser_ler_mem.add_argument(Argumentos.OUTPUT.value, nargs='?', help='arquivo opcional para salvar o dump bruto')

    parser_snapshot = subparsers.add_parser(Comandos.SNAPSHOT.value,
                                            help='le registradores definidos em um perfil de snapshot')
    parser_snapshot.add_argument('--profile', dest=Argumentos.PROFILE.value, default='asr6601',
                                 help='perfil builtin ou caminho para JSON de perfil')
    parser_snapshot.add_argument('--output', dest=Argumentos.OUTPUT.value,
                                 help='arquivo JSON opcional para salvar o snapshot')
    parser_snapshot.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                                 help='imprime snapshot em JSON')

    parser_escrever_reg = subparsers.add_parser(Comandos.ESCREVER_REG.value, help='escrever em um registrador')
    parser_escrever_reg.add_argument(Argumentos.ADDRESS.value, help='endereco do registrador a ser escrito',
                                     type=arg_int)
    parser_escrever_reg.add_argument(Argumentos.VALUE.value, help='valor a ser escrito', type=arg_int)

    parser_jump = subparsers.add_parser(Comandos.JUMP.value, help='executar um jump para um endereco')
    parser_jump.add_argument(Argumentos.ADDRESS.value, help='endereco para onde o jump deve ser feito', type=arg_int)

    parser_ota_pack = subparsers.add_parser(Comandos.OTA_PACK.value,
                                            help='gera pacote OTA com header + firmware binario')
    parser_ota_pack.add_argument(Argumentos.FIRMWARE.value, help='arquivo .bin de firmware')
    parser_ota_pack.add_argument(Argumentos.OUTPUT.value, nargs='?',
                                 help='arquivo de saida (padrao: <firmware>_ota.bin)')

    parser_ota_pack_verify = subparsers.add_parser(Comandos.OTA_PACK_VERIFY.value,
                                                   help='verifica um pacote OTA com header + firmware binario')
    parser_ota_pack_verify.add_argument(Argumentos.INPUT.value, help='arquivo OTA para verificacao')

    parser_ota_pack_inspect = subparsers.add_parser(Comandos.OTA_PACK_INSPECT.value,
                                                    help='inspeciona um pacote OTA e analisa a vector table da app')
    parser_ota_pack_inspect.add_argument(Argumentos.INPUT.value, help='arquivo OTA para inspecao')

    parser_prevalidar = subparsers.add_parser(Comandos.PREVALIDAR.value,
                                              help='valida plano de flash sem conectar no hardware')
    parser_prevalidar.add_argument(Argumentos.ADDR_FILE.value, metavar='<address> <filename>',
                                   help='endereco e nome do arquivo, Ex.: 0x08000000 app.bin', nargs='+')
    parser_prevalidar.add_argument('--strict-app-range', dest=Argumentos.STRICT_APP_RANGE.value, action='store_true',
                                   help='trata endereco fora da faixa da app como erro')
    parser_prevalidar.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                                   help='imprime a pré-validação em JSON')

    parser_firmware_inspect = subparsers.add_parser(Comandos.FIRMWARE_INSPECT.value,
                                                    help='inspeciona firmware raw ou pacote OTA simples localmente')
    parser_firmware_inspect.add_argument(Argumentos.FIRMWARE.value, help='arquivo de firmware ou OTA simples')
    parser_firmware_inspect.add_argument('--base-address', dest=Argumentos.BASE_ADDRESS.value, type=arg_int,
                                         default=ASR_APP_FLASH_START,
                                         help='endereco base esperado da aplicacao')
    parser_firmware_inspect.add_argument('--strict', dest=Argumentos.STRICT.value, action='store_true',
                                         help='retorna erro se a analise estrutural falhar')
    parser_firmware_inspect.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                                         help='imprime inspecao em JSON')

    parser_ota_cript = subparsers.add_parser(
        Comandos.OTA_CRIPT.value,
        help='gera pacote OTA criptografado com trailer v2',
    )
    parser_ota_cript.add_argument(Argumentos.FIRMWARE.value, help='arquivo .bin de firmware sem header OTA')
    parser_ota_cript.add_argument(Argumentos.OUTPUT.value, nargs='?',
                                  help='arquivo de saida (padrao: <firmware>_ota_cript.bin)')
    parser_ota_cript.add_argument('--firmware-version', dest=Argumentos.FIRMWARE_VERSION.value, type=arg_int,
                                  default=1, help='versao numerica do firmware usada na autenticacao')
    parser_ota_cript.add_argument('--key-header', dest=Argumentos.KEY_HEADER.value,
                                  help='header C com BOOT_SECURITY_KEY_BYTES')

    parser_ota_cript_verify = subparsers.add_parser(Comandos.OTA_CRIPT_VERIFY.value,
                                                    help='verifica pacote OTA criptografado')
    parser_ota_cript_verify.add_argument(Argumentos.INPUT.value, help='arquivo OTA criptografado')
    parser_ota_cript_verify.add_argument('--key-header', dest=Argumentos.KEY_HEADER.value,
                                         help='header C com BOOT_SECURITY_KEY_BYTES')

    parser_clear_eeprom = subparsers.add_parser(Comandos.CLEAR_EEPROM.value, help='apagar a EEPROM emulada')
    parser_clear_eeprom.add_argument('--mcu', required=True, choices=('ASR6601CB', 'ASR6601SE'),
                                     help='variante conferida no equipamento')
    subparsers.add_parser(Comandos.HELP.value, help='mostra essa mensagem de ajuda e sai')
    subparsers.add_parser(Comandos.VERSAO.value, help='mostra a versao do ASR Loader')

    for subparser in subparsers.choices.values():
        subparser.add_argument('--v8',
                               help='usar o mapeamento de EEPROM de 1 KiB do firmware v8',
                               action='store_true', default=argparse.SUPPRESS)

    return parser


def main(argv=None):
    parser = cli_build_parser()
    args = parser.parse_args(argv)
    config = None

    try:
        if args.command is None or args.command == Comandos.HELP.value:
            cli_printar_help(parser)
            return 0
        if args.command == Comandos.VERSAO.value:
            timestamp, caminho_build = cli_obter_data_build()
            data_build = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            print('ASR_Loader v%s' % VERSAO_GRAVADOR)
            print('%s' % data_build)
            if args.verbose:
                print('Build source: %s' % caminho_build)
            return 0
        if args.command == Comandos.COMDIAG.value:
            cli_printar_diagnostico(args)
            return 0
        if args.command == Comandos.OTA_PACK.value:
            asr_ota_pack(args)
            print('Pacote OTA gerado com sucesso')
            return 0
        if args.command == Comandos.OTA_PACK_VERIFY.value:
            asr_ota_pack_verify(args)
            print('Pacote OTA verificado com sucesso')
            return 0
        if args.command == Comandos.OTA_PACK_INSPECT.value:
            asr_ota_pack_inspect(args)
            return 0
        if args.command == Comandos.PREVALIDAR.value:
            asr_prevalidar_flash(args)
            return 0
        if args.command == Comandos.FIRMWARE_INSPECT.value:
            relatorio = asr_firmware_inspect(args)
            return 1 if relatorio['errors'] else 0
        if args.command == Comandos.OTA_CRIPT.value:
            asr_ota_cript(args)
            print('Pacote OTA criptografado gerado com sucesso')
            return 0
        if args.command == Comandos.OTA_CRIPT_VERIFY.value:
            asr_ota_cript_verify(args)
            print('Pacote OTA validado com sucesso')
            return 0

        if args.command == 'bin_empacotar':
            dados, metadados = separar_rodape(args.arquivo.read_bytes())
            if metadados is not None:
                raise ValueError('O binário já possui metadados ASRPROD')
            args.saida.write_bytes(acrescentar_rodape(dados, args.versao, args.variante,
                                                      args.tipo, args.origem, args.aplicacao))
            return 0
        if args.command in ('bin_inspect', 'bin_extrair'):
            dados, metadados = separar_rodape(args.arquivo.read_bytes())
            if args.command == 'bin_extrair':
                args.saida.write_bytes(dados)
            elif metadados is None:
                raise ValueError('Binário sem metadados ASRPROD')
            else:
                print(formatar_tabela_rodape(metadados, len(dados)))
            return 0

        if args.command == 'producao_inspect':
            imagem, versao = ler_binario_producao(args.arquivo, args.mcu)
            print(f'Produção PR439v3 válida. Firmware {versao}, {args.mcu}, {len(imagem)} bytes graváveis.')
            return 0

        if args.command == 'otp_producao_inspect':
            mostrar_previa_otp_producao(args.arquivo, args.mcu, args.exibir_chave)
            return 0

        if args.boot_reset_delay < 0 or args.boot_release_delay < 0:
            raise Exception('ERROR: os tempos de boot automatico devem ser maiores ou iguais a zero')

        config = RuntimeConfig(
            verbose=args.verbose,
            com_timeout=args.timeout if args.timeout is not None else TIMEOUT_DEFAULT,
            apaga_eeprom=not args.eeprom,
            baud=args.baud,
            portas_disponiveis=get_lista_portas_com() if args.port is None else [args.port],
            auto_boot=not args.no_auto_boot,
            boot_reset_delay=args.boot_reset_delay,
            boot_release_delay=args.boot_release_delay,
            log_file=args.log_file,
            trace_json=args.trace_json,
            v8=args.v8,
        )
        config.log('command=%s argv=%s baud=%d timeout=%s portas=%s' % (
            args.command,
            '[omitido]' if (
                args.command == Comandos.ESCREVER_OTP.value or getattr(args, 'producao', None) or getattr(args,
                                                                                                          'producao_bin',
                                                                                                          False))
            else (argv if argv is not None else sys.argv[1:]),
            args.baud,
            args.timeout,
            ','.join(config.portas_disponiveis),
        ))

        if args.port is None and not getattr(args, 'json', False):
            print("Encontrado %d serial ports" % len(config.portas_disponiveis))

        asr_mcu = ASRLoader(config)

        if args.command == Comandos.JUMP.value:
            asr_jump(args, asr_mcu, config)
            print('Jump executado com sucesso')
        elif args.command == Comandos.FLASH.value:
            gravado = asr_flash(args, asr_mcu, config)
            if gravado:
                print('Gravado com sucesso')
        elif args.command == Comandos.ERASE.value:
            asr_erase(args, asr_mcu, config)
            print('Apagado com sucesso')
        elif args.command == Comandos.VERIFY.value:
            asr_verify(args, asr_mcu, config)
            print('Verificacao completa! Flash igual ao arquivo.')
        elif args.command == Comandos.ESCREVER_OTP.value:
            asr_escrever_otp(args, asr_mcu, config)
            print('Escrita na OTP com sucesso')
        elif args.command == Comandos.DIAGNOSTICAR_OTP.value:
            diagnosticar_otp(args, asr_mcu)
        elif args.command == Comandos.DIAGNOSTICAR_FLASH_ASR.value:
            diagnosticar_flash_asr(args, asr_mcu)
        elif args.command == Comandos.LER_OTP.value:
            data = asr_ler_otp(args, asr_mcu, config)
            print('OTP data: %s' % binascii.hexlify(data))
        elif args.command == Comandos.ESCREVER_OPT0.value:
            asr_escrever_opt0(args, asr_mcu, config)
            print('Escrita na OPT0 com sucesso')
        elif args.command == Comandos.LER_OPT0.value:
            opt0 = asr_ler_opt0(args, asr_mcu, config)
            print('OPT0 data: %s %s' % (hex(opt0[0]), hex(opt0[1])))
        elif args.command == Comandos.ESCREVER_OPT1.value:
            asr_escrever_opt1(args, asr_mcu, config)
            print('Escrita na OPT1 com sucesso')
        elif args.command == Comandos.LER_OPT1.value:
            opt1 = asr_ler_opt1(args, asr_mcu, config)
            print('OPT1 data: %s %s' % (hex(opt1[0]), hex(opt1[1])))
        elif args.command == Comandos.RESET.value:
            asr_sw_reset(args, asr_mcu, config)
            print('Reset via software')
        elif args.command == Comandos.DOCTOR.value:
            relatorio = cli_montar_doctor(args, config, asr_mcu)
            if args.json:
                print(json.dumps(relatorio, indent=2, ensure_ascii=False))
            else:
                cli_printar_doctor(relatorio)
            return 1 if any(item['status'] == 'fail' for item in relatorio['checks']) else 0
        elif args.command == Comandos.TESTEBOOT.value:
            if args.sweep:
                asr_probe_sweep(args, lambda: ASRLoader(config), config)
                if not args.json:
                    print('Teste de boot sweep concluído')
            else:
                if args.json:
                    with contextlib.redirect_stdout(io.StringIO()):
                        asr_probe(args, asr_mcu, config)
                    print(json.dumps({'ok': True, 'baud': args.baud, 'ports': config.portas_disponiveis},
                                     indent=2, ensure_ascii=False))
                else:
                    asr_probe(args, asr_mcu, config)
                    print('Teste de boot concluído: boot respondeu')
        elif args.command == Comandos.HW_RESET.value:
            asr_hw_reset(args, asr_mcu, config)
            print('Reset via hardware')
        elif args.command in (
                Comandos.DTR1.value,
                Comandos.DTR0.value,
                Comandos.RTS1.value,
                Comandos.RTS0.value):
            asr_controlar_linha_serial(args, asr_mcu, config)
        elif args.command == Comandos.SERIAL.value:
            sn = asr_serial_asr(args, asr_mcu, config)
            print('Serial: %s' % sn.hex())
        elif args.command == Comandos.IDENTIFICAR_MCU.value:
            asr_identificar_mcu(args, asr_mcu, config)
        elif args.command == Comandos.MAPA_FLASH.value:
            asr_mapa_memoria(args, asr_mcu, config, 'Flash interna', ler_bytes=True)
        elif args.command == Comandos.MAPA_SRAM.value:
            asr_mapa_memoria(args, asr_mcu, config, 'SRAM', ler_bytes=True)
        elif args.command == Comandos.MAPA_EEPROM.value:
            asr_mapa_memoria(args, asr_mcu, config, 'EEPROM emulada', ler_bytes=True)
        elif args.command == Comandos.MAPA_MEMORIA.value:
            asr_mapa_memoria(args, asr_mcu, config)
        elif args.command == Comandos.ESCREVER_REG.value:
            asr_escrever_reg(args, asr_mcu, config)
            print('Registrador escrito com sucesso')
        elif args.command == Comandos.LER_REG.value:
            valor_reg = asr_ler_reg(args, asr_mcu, config)
            print('Valor do registrador: 0x%08X' % valor_reg[0])
        elif args.command == Comandos.LER_MEM.value:
            asr_ler_mem(args, asr_mcu, config)
        elif args.command == Comandos.SNAPSHOT.value:
            asr_snapshot(args, asr_mcu, config)
        elif args.command == Comandos.VERSAO_BOOTLOADER.value:
            versao = asr_versao_bootloader(args, asr_mcu, config)
            versao_raw = versao[0]
            versao_bytes = ' '.join('%02X' % byte for byte in struct.pack('<I', versao_raw))
            print('VERSAO retornada pelo bootloader (valor bruto): 0x%08X (%d)' % (versao_raw, versao_raw))
            print('Bytes retornados: %s' % versao_bytes)
        elif args.command == Comandos.CLEAR_EEPROM.value:
            asr_clean_eeprom(args, asr_mcu, config)
            print('Eeprom emulada apagada com sucesso')
        else:
            cli_printar_help(parser)
        return 0
    except Exception as excessao:
        if config is not None:
            config.log('ERROR: %s' % excessao)
        print(str(excessao), file=sys.stderr)
        return 1
    finally:
        if config is not None:
            config.close_log()
            config.close_trace()
