import zlib
import serial.tools.list_ports as list_ports


"""Converte um argumento para int, aceitando decimal e hexadecimal."""
def arg_int(x):
    return int(x, 0)


"""Calcula o CRC32 de um arquivo."""
def get_crc32(pacote):
    with open(pacote, 'rb') as arquivo:
        return zlib.crc32(arquivo.read()) & 0xFFFFFFFF


"""Retorna a lista de portas seriais disponíveis."""
def get_lista_portas_com():
    return sorted(porta.device for porta in list_ports.comports())


"""Exibe as portas seriais disponíveis em ordem inversa."""
def get_dispositivo_conectado(lista_portas):
    for each_port in reversed(lista_portas):
        print("Serial port %s" % each_port)
