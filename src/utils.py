import zlib

import serial.tools.list_ports as list_ports


def arg_int(x):
    """Converte um argumento para int, aceitando decimal e hexadecimal."""
    return int(x, 0)


def get_crc32(pacote):
    """Calcula o CRC32 de um arquivo."""
    with open(pacote, 'rb') as arquivo:
        return zlib.crc32(arquivo.read()) & 0xFFFFFFFF


def get_lista_portas_com():
    """Retorna a lista de portas seriais disponíveis."""
    return sorted(porta.device for porta in list_ports.comports())


def get_dispositivo_conectado(lista_portas):
    """Exibe as portas seriais disponíveis em ordem inversa."""
    for each_port in reversed(lista_portas):
        print("Serial port %s" % each_port)

