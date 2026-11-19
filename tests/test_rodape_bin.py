import binascii
import hashlib
import struct
from types import SimpleNamespace

import pytest

from src import comandos
from src.cli import main
from src.rodape_bin import TCHE, acrescentar_rodape, separar_rodape


@pytest.mark.parametrize('tipo,tem_tche', [(0, True), (0, False), (6, True)])
def test_bin_inspect_mostra_todos_os_campos(tmp_path, capsys, tipo, tem_tche):
    """Confere a tabela do CLI e distingue tamanho armazenado e extraído no OTA."""
    imagem = bytes(range(64))
    pacote = acrescentar_rodape(imagem, 900, 2, tipo, 0, 0x08002000)
    crc, = struct.unpack_from('<I', pacote, len(pacote) - 10)
    arquivo = tmp_path / 'firmware.bin'
    arquivo.write_bytes(pacote if tem_tche else pacote[:-len(TCHE)])
    assert main(['bin_inspect', str(arquivo)]) == 0
    linhas = capsys.readouterr().out.splitlines()
    assert linhas[0].startswith('Metadados do binário (ASRPROD)')
    assert [linha.split()[0] for linha in linhas[2:15]] == [
        '0x00', '0x08', '0x0A', '0x0C', '0x10', '0x12', '0x13',
        '0x14', '0x18', '0x1A', '0x1E', '0x22', '0x42',
    ]
    assert linhas[13].endswith(hashlib.sha256(imagem).hexdigest().upper())
    assert linhas[14].endswith(f'0x{crc:08X}')
    assert all('TCHE' not in linha for linha in linhas)
    tamanho_extraido = 70 if tipo == 6 else 64
    assert linhas[15:] == [f'Bytes após extração: {tamanho_extraido}']


@pytest.mark.parametrize('tipo', range(7))
def test_metadados_recuperam_binario_original(tipo: int):
    origem = 0 if tipo in (5, 6) else 0x08000000
    dados = bytes(range(256)) * 3
    if tipo in (5, 6):
        dados += TCHE
    pacote = acrescentar_rodape(dados, 900, 2, tipo, origem, 0x08002000)
    assert pacote[-76:-68] == b'ASRPROD\0'
    assert pacote[-6:] == TCHE
    gravavel, metadados = separar_rodape(pacote)
    assert gravavel == dados
    assert metadados['versao'] == 900
    assert metadados['tipo'] == tipo
    corrompido = bytes([pacote[0] ^ 1]) + pacote[1:]
    with pytest.raises(ValueError, match=r'Metadados do binário \(ASRPROD\) inválidos'):
        separar_rodape(corrompido)


@pytest.mark.parametrize('tipo,origem', [(2, 0x08000000), (5, 0), (6, 0)])
def test_flash_e_verify_excluem_metadados(tmp_path, monkeypatch, tipo, origem):
    dados = bytes(range(256)) * 3
    if tipo in (5, 6):
        dados += TCHE
    arquivo = tmp_path / 'firmware.bin'
    arquivo.write_bytes(acrescentar_rodape(dados, 900, 2, tipo, origem, 0x08002000))
    eventos = []
    simulador = SimpleNamespace(
        erase=lambda *args: eventos.append(('apagar', *args)),
        flash=lambda *args: eventos.append(('gravar', *args)),
        verify=lambda *args: eventos.append(('verificar', *args)),
        sw_reset=lambda modo: None,
    )
    monkeypatch.setattr(comandos, 'asr_conectar', lambda *args: True)
    config = SimpleNamespace(portas_disponiveis=[], apaga_eeprom=False, verbose=False)
    param = SimpleNamespace(addr_file=[hex(origem), str(arquivo)], baud=115200)
    assert comandos.asr_flash(param, simulador, config)
    assert eventos == [
        ('apagar', origem, len(dados)),
        ('gravar', origem, dados[:512]),
        ('gravar', origem + 512, dados[512:]),
        ('verificar', origem, len(dados), binascii.crc32(dados)),
    ]
    eventos.clear()
    param = SimpleNamespace(filename=str(arquivo), address=origem, baud=115200)
    comandos.asr_verify(param, simulador, config)
    assert eventos == [('verificar', origem, len(dados), binascii.crc32(dados))]
