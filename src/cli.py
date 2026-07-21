import argparse
import binascii
import json
import platform
import struct
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
import serial
from .comandos import (
    asr_clean_eeprom,
    asr_controlar_linha_serial,
    asr_erase,
    asr_escrever_opt0,
    asr_escrever_opt1,
    asr_escrever_otp,
    asr_escrever_reg,
    asr_flash,
    asr_jump,
    asr_ler_opt0,
    asr_ler_opt1,
    asr_ler_mem,
    asr_ler_otp,
    asr_ler_reg,
    asr_ota_pack,
    asr_ota_pack_inspect,
    asr_ota_pack_verify,
    asr_ota_assinado,
    asr_ota_assinado_verify,
    asr_ota_cript,
    asr_ota_ota_verify,
    asr_serial_asr,
    asr_hw_reset,
    asr_sw_reset,
    asr_verify,
    asr_versao_bootloader,
)
from .constantes import BAUD_DEFAULT, TIMEOUT_DEFAULT, VERSAO_GRAVADOR
from .ASRLoader import ASRLoader
from .runtime import RuntimeConfig
from .utils import arg_int, get_lista_portas_com, get_lista_portas_info


class Comandos(str, Enum):
    MAKE = 'make'
    ERASE = 'erase'
    FLASH = 'flash'
    VERIFY = 'verify'
    RESET = 'reset'
    HW_RESET = 'hw_reset'
    DTR1 = 'dtr1'
    DTR0 = 'dtr0'
    RTS1 = 'rts1'
    RTS0 = 'rts0'
    CLEAR_EEPROM = 'clear_eeprom'
    SERIAL = 'serial'
    DIAG = 'diag'

    OTA_PACK = 'ota_pack'
    OTA_PACK_VERIFY = 'ota_pack_verify'
    OTA_PACK_INSPECT = 'ota_pack_inspect'
    OTA_ASSINADO = 'ota_assinado'
    OTA_ASSINADO_VERIFY = 'ota_assinado_verify'
    OTA_CRIPT = 'ota_cript'
    OTA_CRIPT_VERIFY = 'ota_cript_verify'

    JUMP = 'jump'

    VERSAO_BOOTLOADER = 'versao_bootloader'

    LER_OTP = 'ler_otp'
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
    if not diagnostico['ports']:
        print('  Nenhuma porta serial encontrada')
        return

    for porta in diagnostico['ports']:
        vid = ('0x%04X' % porta['vid']) if porta['vid'] is not None else ''
        pid = ('0x%04X' % porta['pid']) if porta['pid'] is not None else ''
        vid_pid = '%s/%s' % (vid, pid) if vid or pid else ''
        print('  %s' % porta['device'])
        print('    Descricao : %s' % (porta['description'] or ''))
        print('    HWID      : %s' % (porta['hwid'] or ''))
        print('    VID/PID   : %s' % vid_pid)
        print('    Fabricante: %s' % (porta['manufacturer'] or ''))
        print('    Produto   : %s' % (porta['product'] or ''))


def cli_adicionar_argumentos(argumentos):
    argumentos.add_argument(Opcoes.PORT.long, Opcoes.PORT.short, help=Opcoes.PORT.texto)
    argumentos.add_argument(Opcoes.BAUD.long, Opcoes.BAUD.short, help=Opcoes.BAUD.texto, type=int, default=BAUD_DEFAULT)
    argumentos.add_argument(Opcoes.VERBOSE.long, Opcoes.VERBOSE.short, help=Opcoes.VERBOSE.texto, action='store_true')
    argumentos.add_argument(Opcoes.TIMEOUT.long, Opcoes.TIMEOUT.short, help=Opcoes.TIMEOUT.texto, type=int,
                            default=TIMEOUT_DEFAULT)
    argumentos.add_argument(Opcoes.EEPROM.long, Opcoes.EEPROM.short, help=Opcoes.EEPROM.texto, action='store_true')
    argumentos.add_argument('--no-auto-boot', help='nao aciona DTR/RTS automaticamente antes de conectar',
                            action='store_true')
    argumentos.add_argument('--boot-reset-delay', help='tempo em segundos mantendo o reset ativo via RTS, default 0.1s',
                            type=float, default=0.1)
    argumentos.add_argument('--boot-release-delay',
                            help='tempo em segundos antes de liberar o modo boot via DTR, default 0.1s',
                            type=float, default=0.1)


def cli_adicionar_comando_linha_serial(subparsers, comando, linha, estado):
    parser_linha = subparsers.add_parser(comando, help='seta %s=%d para teste de hardware' % (
        linha.upper(), 1 if estado else 0))
    parser_linha.add_argument('--hold', dest=Argumentos.HOLD.value, type=float,
                              help='tempo em segundos mantendo a porta aberta; sem este parametro, aguarda Ctrl+C')
    parser_linha.set_defaults(control_line=linha, control_state=estado)


def cli_build_parser():
    parser = argparse.ArgumentParser()
    cli_adicionar_argumentos(parser)

    msg_help = 'run asr_loader.py {command} -h'
    subparsers = parser.add_subparsers(dest='command', help=msg_help)

    parser_erase = subparsers.add_parser(Comandos.ERASE.value, help='apagar determinada area da flash')
    parser_erase.add_argument(Argumentos.ADDRESS.value, help='endereco da flash a ser apagada', type=arg_int)
    parser_erase.add_argument(Argumentos.SIZE.value, help='quantidade de bytes a serem apagados', type=arg_int)

    parser_flash = subparsers.add_parser(Comandos.FLASH.value, help='apagar e gravar a flash')
    parser_flash.add_argument(Argumentos.ADDR_FILE.value, metavar='<address> <filename>',
                              help='endereco e nome do arquivo, Ex.: 0x08000000 app.bin', nargs='+')

    parser_escrever_otp = subparsers.add_parser(Comandos.ESCREVER_OTP.value,
                                                help='escrever em uma area da opt da flash')
    parser_escrever_otp.add_argument(Argumentos.ADDRESS.value, help='endereco flash otp', type=arg_int)
    parser_escrever_otp.add_argument(Argumentos.DATA.value, help='dado a ser escrito na flash (hexadecimal)')

    parser_ler_otp = subparsers.add_parser(Comandos.LER_OTP.value, help='ler a area da otp da flash')
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
    parser_diag = subparsers.add_parser(Comandos.DIAG.value, help='mostra diagnostico do ambiente e portas seriais')
    parser_diag.add_argument('--json', dest=Argumentos.JSON.value, action='store_true',
                             help='imprime o diagnostico em JSON')
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

    parser_ota_assinado = subparsers.add_parser(Comandos.OTA_ASSINADO.value,
                                                help='gera pacote OTA assinado com trailer de autenticacao')
    parser_ota_assinado.add_argument(Argumentos.FIRMWARE.value, help='arquivo .bin de firmware sem header OTA')
    parser_ota_assinado.add_argument(Argumentos.OUTPUT.value, nargs='?',
                                     help='arquivo de saida (padrao: <firmware>_ota_assinado.bin)')
    parser_ota_assinado.add_argument('--firmware-version', dest=Argumentos.FIRMWARE_VERSION.value, type=arg_int,
                                     default=1, help='versao numerica do firmware usada na autenticacao')
    parser_ota_assinado.add_argument('--key-header', dest=Argumentos.KEY_HEADER.value,
                                     help='header C com BOOT_SECURITY_KEY_BYTES')

    parser_ota_assinado_verify = subparsers.add_parser(Comandos.OTA_ASSINADO_VERIFY.value,
                                                       help='verifica um pacote OTA assinado com trailer de autenticacao')
    parser_ota_assinado_verify.add_argument(Argumentos.INPUT.value, help='arquivo OTA assinado para verificacao')
    parser_ota_assinado_verify.add_argument('--key-header', dest=Argumentos.KEY_HEADER.value,
                                            help='header C com BOOT_SECURITY_KEY_BYTES')

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

    subparsers.add_parser(Comandos.CLEAR_EEPROM.value, help='apagar a eeprom emulada')
    subparsers.add_parser(Comandos.HELP.value, help='mostra essa mensagem de ajuda e sai')
    subparsers.add_parser(Comandos.VERSAO.value, help='mostra a versao do ASR Loader')

    return parser


def main(argv=None):
    parser = cli_build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is None or args.command == Comandos.HELP.value:
            cli_printar_help(parser)
            return
        if args.command == Comandos.VERSAO.value:
            timestamp, caminho_build = cli_obter_data_build()
            data_build = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            print('ASR_Loader v%s' % VERSAO_GRAVADOR)
            print('%s' % data_build)
            if args.verbose:
                print('Build source: %s' % caminho_build)
            return
        if args.command == Comandos.DIAG.value:
            cli_printar_diagnostico(args)
            return
        if args.command == Comandos.OTA_PACK.value:
            asr_ota_pack(args)
            print('Pacote OTA gerado com sucesso')
            return
        if args.command == Comandos.OTA_PACK_VERIFY.value:
            asr_ota_pack_verify(args)
            print('Pacote OTA verificado com sucesso')
            return
        if args.command == Comandos.OTA_PACK_INSPECT.value:
            asr_ota_pack_inspect(args)
            return
        if args.command == Comandos.OTA_ASSINADO.value:
            asr_ota_assinado(args)
            print('Pacote OTA assinado gerado com sucesso')
            return
        if args.command == Comandos.OTA_ASSINADO_VERIFY.value:
            asr_ota_assinado_verify(args)
            print('Pacote OTA assinado verificado com sucesso')
            return
        if args.command == Comandos.OTA_CRIPT.value:
            asr_ota_cript(args)
            print('Pacote OTA criptografado gerado com sucesso')
            return
        if args.command == Comandos.OTA_CRIPT_VERIFY.value:
            asr_ota_ota_verify(args)
            print('Pacote OTA validado com sucesso')
            return

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
        )

        if args.port is None:
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
        elif args.command == Comandos.HW_RESET.value:
            if asr_hw_reset(args, asr_mcu, config):
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
        elif args.command == Comandos.ESCREVER_REG.value:
            asr_escrever_reg(args, asr_mcu, config)
            print('Registrador escrito com sucesso')
        elif args.command == Comandos.LER_REG.value:
            valor_reg = asr_ler_reg(args, asr_mcu, config)
            print('Valor do registrador: 0x%08X' % valor_reg[0])
        elif args.command == Comandos.LER_MEM.value:
            asr_ler_mem(args, asr_mcu, config)
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
    except Exception as excessao:
        print(str(excessao))
