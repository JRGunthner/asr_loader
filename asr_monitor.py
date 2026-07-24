import serial
from serial.tools import list_ports


def buscar_portas_com():
    return list(list_ports.comports())


def selecionar_porta():
    portas = buscar_portas_com()
    if not portas:
        raise RuntimeError('Nenhuma porta serial disponível')

    print('Portas disponíveis')
    for indice, porta_disponivel in enumerate(portas):
        print('[{}] {}'.format(indice, porta_disponivel.description))

    while True:
        try:
            indice = int(input('\nSelecione a porta pelo número\n> '))
            return portas[indice].device
        except (ValueError, IndexError):
            print('Porta inválida')


def selecionar_baudrate():
    while True:
        try:
            baudrate = int(input('\nSelecione o baud rate\n> '))
            if baudrate <= 0:
                raise ValueError
            return baudrate
        except ValueError:
            print('Baud rate inválido')


def abrir_conexao(porta, baudrate):
    conexao_serial = serial.Serial(port=None, baudrate=baudrate, timeout=1)
    conexao_serial.dtr = False
    conexao_serial.rts = False
    conexao_serial.port = porta
    conexao_serial.open()
    return conexao_serial


def main():
    try:
        porta = selecionar_porta()
        baudrate = selecionar_baudrate()
        conexao_serial = abrir_conexao(porta, baudrate)
    except (RuntimeError, serial.SerialException) as erro:
        print('\nNão foi possível conectar: {}'.format(erro))
        return 1

    print('\nConexão estabelecida')
    try:
        while conexao_serial.is_open:
            dados = conexao_serial.readline()
            if dados:
                print(dados.decode('utf-8', errors='replace').rstrip())
    except serial.SerialException as erro:
        print('\nErro na conexão serial: {}'.format(erro))
    except KeyboardInterrupt:
        print('\nMonitor interrompido')
    finally:
        if conexao_serial.is_open:
            conexao_serial.close()

    print('\nConexão encerrada')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
