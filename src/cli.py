import argparse
import binascii
import struct
from .comandos import (
    tremo_clean_eeprom,
    tremo_erase,
    tremo_escrever_opt0,
    tremo_escrever_opt1,
    tremo_escrever_otp,
    tremo_escrever_reg,
    tremo_flash,
    tremo_jump,
    tremo_ler_opt0,
    tremo_ler_opt1,
    tremo_ler_otp,
    tremo_ler_reg,
    tremo_ota_pack,
    tremo_serial_asr,
    tremo_sw_reset,
    tremo_verify,
    tremo_versao_bootloader,
)
from .constantes import BAUD_DEFAULT, TIMEOUT_DEFAULT, VERSAO_GRAVADOR
from .tremoLoader import TremoLoader
from .runtime import RuntimeConfig
from .utils import arg_int, get_lista_portas_com


def tremo_print_help(help_parser):
    print("Tremo Loader v%s" % VERSAO_GRAVADOR)
    help_parser.print_help()
    print("\nPortas seriais disponiveis:")
    portas = get_lista_portas_com()
    if len(portas) == 0:
        print("  Nenhuma porta serial encontrada")
    else:
        for porta in portas:
            print(" ", porta)


def tremo_add_argumentos(argumentos):
    msg = 'porta serial'
    argumentos.add_argument('--port', '-p', help=msg)

    msg = 'baudrate, default 921600'
    argumentos.add_argument('--baud', '-b', help=msg, type=int, default=BAUD_DEFAULT)

    msg = 'modo verbose para debug'
    argumentos.add_argument('--verbose', '-v', help=msg, action='store_true')

    msg = 'timeout da serial em segundos, default 2s'
    argumentos.add_argument('--timeout', '-t', help=msg, type=int, default=TIMEOUT_DEFAULT)

    msg = 'mantém os dados da eeprom emulada'
    argumentos.add_argument('--eeprom', '-e', help=msg, action='store_true')


def build_parser():
    parser = argparse.ArgumentParser()
    tremo_add_argumentos(parser)

    msg_help = 'run tremo_loader.py {command} -h'
    subparsers = parser.add_subparsers(dest='command', help=msg_help)

    parser_erase = subparsers.add_parser('erase', help='apagar determinada area da flash')
    parser_erase.add_argument('address', help='endereco da flash a ser apagada', type=arg_int)
    parser_erase.add_argument('size', help='quantidade de bytes a serem apagados', type=arg_int)

    parser_flash = subparsers.add_parser('flash', help='apagar e gravar a flash')
    parser_flash.add_argument('addr_file', metavar='<address> <filename>', help='endereco e nome do arquivo, Ex.: 0x08000000 app.bin', nargs='+')

    parser_escrever_otp = subparsers.add_parser('escrever_otp', help='escrever em uma area da opt da flash')
    parser_escrever_otp.add_argument('address', help='endereco flash otp', type=arg_int)
    parser_escrever_otp.add_argument('data', help='dado a ser escrito na flash (hexadecimal)')

    parser_ler_otp = subparsers.add_parser('ler_otp', help='ler a area da otp da flash')
    parser_ler_otp.add_argument('address', help='endereco flash otp', type=arg_int)
    parser_ler_otp.add_argument('size', help='endereco flash otp', type=arg_int)

    parser_escrever_opt0 = subparsers.add_parser('escrever_opt0', help='escrever na area opt0 da flash')
    parser_escrever_opt0.add_argument('opt0_l', help='valor msb a ser escrito', type=arg_int)
    parser_escrever_opt0.add_argument('opt0_h', help='valor lsb a ser escrito', type=arg_int)

    subparsers.add_parser('ler_opt0', help='ler a area opt0 da flash')

    parser_escrever_opt1 = subparsers.add_parser('escrever_opt1', help='escrever na area opt1 da flash')
    parser_escrever_opt1.add_argument('opt1_l', help='valor msb a ser escrito', type=arg_int)
    parser_escrever_opt1.add_argument('opt1_h', help='valor lsb a ser escrito', type=arg_int)

    subparsers.add_parser('ler_opt1', help='ler a area opt1 da flash')
    subparsers.add_parser('serial', help='ler o serial do ASR')
    subparsers.add_parser('reset', help='resetar o ASR')

    parser_verify = subparsers.add_parser('verify', help='verificar o conteudo da flash')
    parser_verify.add_argument('address', help='endereco da flash a ser verificado', type=arg_int)
    parser_verify.add_argument('filename', help='arquivo para comparar com a flash')

    subparsers.add_parser('versao_bootloader', help='ler o version number bruto retornado pelo comando VERSION do bootloader')

    parser_ler_reg = subparsers.add_parser('ler_reg', help='ler o conteudo de um registrador')
    parser_ler_reg.add_argument('address', help='endereco do registrador a ser lido', type=arg_int)

    parser_escrever_reg = subparsers.add_parser('escrever_reg', help='escrever em um registrador')
    parser_escrever_reg.add_argument('address', help='endereco do registrador a ser escrito', type=arg_int)
    parser_escrever_reg.add_argument('value', help='valor a ser escrito', type=arg_int)

    parser_jump = subparsers.add_parser('jump', help='executar um jump para um endereco')
    parser_jump.add_argument('address', help='endereco para onde o jump deve ser feito', type=arg_int)

    parser_ota_pack = subparsers.add_parser('ota_pack', help='gera pacote OTA com header + firmware binario')
    parser_ota_pack.add_argument('firmware', help='arquivo .bin de firmware')
    parser_ota_pack.add_argument('output', nargs='?', help='arquivo de saida (padrao: <firmware>_ota.bin)')

    subparsers.add_parser('help', help='mostra essa mensagem de ajuda e sai')
    subparsers.add_parser('versao', help='mostra a versao do tremo_loader')

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is None or args.command == 'help':
            tremo_print_help(parser)
            return
        if args.command == 'versao':
            print("Tremo Loader v%s" % VERSAO_GRAVADOR)
            return
        if args.command == 'ota_pack':
            tremo_ota_pack(args)
            print('Pacote OTA gerado com sucesso')
            return

        config = RuntimeConfig(
            verbose=args.verbose,
            com_timeout=args.timeout if args.timeout is not None else TIMEOUT_DEFAULT,
            apaga_eeprom=not args.eeprom,
            baud=args.baud,
            portas_disponiveis=get_lista_portas_com() if args.port is None else [args.port],
        )

        if args.port is None:
            print("Encontrado %d serial ports" % len(config.portas_disponiveis))

        tremo = TremoLoader(config)

        if args.command == 'jump':
            tremo_jump(args, tremo, config)
            print('Jump executado com sucesso')
        elif args.command == 'flash':
            gravado = tremo_flash(args, tremo, config)
            if gravado:
                print('Gravado com sucesso')
        elif args.command == 'erase':
            tremo_erase(args, tremo, config)
            print('Apagado com sucesso')
        elif args.command == 'verify':
            tremo_verify(args, tremo, config)
            print('Verificacao completa! Flash igual ao arquivo.')
        elif args.command == 'escrever_otp':
            tremo_escrever_otp(args, tremo, config)
            print('Escrita na OTP com sucesso')
        elif args.command == 'ler_otp':
            data = tremo_ler_otp(args, tremo, config)
            print('OTP data: %s' % binascii.hexlify(data))
        elif args.command == 'escrever_opt0':
            tremo_escrever_opt0(args, tremo, config)
            print('Escrita na OPT0 com sucesso')
        elif args.command == 'ler_opt0':
            opt0 = tremo_ler_opt0(args, tremo, config)
            print('OPT0 data: %s %s' % (hex(opt0[0]), hex(opt0[1])))
        elif args.command == 'escrever_opt1':
            tremo_escrever_opt1(args, tremo, config)
            print('Escrita na OPT1 com sucesso')
        elif args.command == 'ler_opt1':
            opt1 = tremo_ler_opt1(args, tremo, config)
            print('OPT1 data: %s %s' % (hex(opt1[0]), hex(opt1[1])))
        elif args.command == 'reset':
            tremo_sw_reset(args, tremo, config)
            print('Reset via software')
        elif args.command == 'serial':
            sn = tremo_serial_asr(args, tremo, config)
            print('Serial: %s' % binascii.hexlify(sn))
        elif args.command == 'escrever_reg':
            tremo_escrever_reg(args, tremo, config)
            print('Registrador escrito com sucesso')
        elif args.command == 'ler_reg':
            valor_reg = tremo_ler_reg(args, tremo, config)
            print('Valor do registrador: 0x%s' % valor_reg[0])
        elif args.command == 'versao_bootloader':
            versao = tremo_versao_bootloader(args, tremo, config)
            versao_raw = versao[0]
            versao_bytes = ' '.join('%02X' % byte for byte in struct.pack('<I', versao_raw))
            print('VERSION retornado pelo bootloader (valor bruto): 0x%08X (%d)' % (versao_raw, versao_raw))
            print('Bytes retornados: %s' % versao_bytes)
        elif args.command == 'clear_eeprom':
            tremo_clean_eeprom(args, tremo, config)
            print('Eeprom emulada apagada com sucesso')
        else:
            tremo_print_help(parser)
    except Exception as excessao:
        print(str(excessao))
