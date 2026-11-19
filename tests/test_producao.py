import hashlib
import json
import struct
import zlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src import cli
from src.comandos import asr_flash
from src.exceptions import CmdExcessao
from src.producao import APAGADO, FLASH_INICIO, classificar_registro, montar_registro

CHAVE_TESTE = bytes(range(1, 33))
BASE_TESTE = 0x10001C00
SERIAL_TESTE = bytes(range(21, 29))
DATA_TESTE = datetime(2026, 11, 18, 12, 30, tzinfo=timezone.utc)


def _montar_registro_teste(chave, versao):
    return montar_registro(chave, versao, 'ASR6601CB', DATA_TESTE)


def test_layout_otp_de_96_bytes():
    registro = montar_registro(CHAVE_TESTE, 900, 'ASR6601SE', DATA_TESTE)
    assert len(registro) == 96
    assert registro[:8] == b'\x01\x60\x00\x09EEPR'
    assert registro[8:40] == CHAVE_TESTE
    assert registro[40:56] == b'ASR6601SE' + bytes(7)
    assert registro[56:60] == struct.pack('<HH', 256, 64)
    assert registro[60:80] == b'2026-11-18T09:30:00\0'
    crc = zlib.crc32(registro[:80])
    assert registro[80:88] == struct.pack('<II', crc, crc ^ 0xffffffff)
    assert registro[88:] == b'CONFOTP1'
    assert classificar_registro(registro) == ('VÁLIDO', 900)


def test_quadro_antigo_com_data_utc_continua_valido():
    registro = _montar_registro_teste(CHAVE_TESTE, 900)
    corpo = registro[:60] + b'2026-11-18T12:30:00Z'
    crc = zlib.crc32(corpo)
    quadro_antigo = corpo + struct.pack('<II', crc, crc ^ 0xFFFFFFFF) + registro[88:]
    assert classificar_registro(quadro_antigo) == ('VÁLIDO', 900)


class GravadorSimulado:
    def __init__(self, memoria=APAGADO):
        self.memoria = bytearray(memoria)
        self.unidades = []
        self.eventos = []
        self.ser = None
        self.sessao_reservada = False
        self.leituras = 0
        self.falha_leitura = None
        self.falha_etapa = None
        self.falha_flash = False
        self.serial = SERIAL_TESTE

    @staticmethod
    def ler_reg(endereco):
        pytest.fail(f'Leitura de registrador não configurada no endereço 0x{endereco:08X}')

    def set_port(self, _porta):
        self.eventos.append('porta')
        self.ser = self

    def close(self):
        self.eventos.append('fechar')

    def conectar(self):
        self.eventos.append('conectar')

    def set_baudrate(self, baud):
        pass

    def serial_asr(self):
        return self.serial

    def ler_otp(self, endereco, tamanho):
        assert (endereco, tamanho) == (BASE_TESTE, len(APAGADO))
        self.leituras += 1
        if self.leituras == self.falha_leitura:
            raise OSError(CHAVE_TESTE.hex())
        return bytes(self.memoria)

    def escrever_otp(self, endereco, dados):
        offset = endereco - BASE_TESTE
        assert offset % 8 == 0 and len(dados) == 8
        assert offset not in self.unidades
        assert self.memoria[offset:offset + 8] == APAGADO[:8]
        self.unidades.append(offset)
        if len(self.unidades) == self.falha_etapa:
            self.memoria[offset] &= dados[0]
            raise OSError(CHAVE_TESTE.hex())
        self.memoria[offset:offset + 8] = dados

    def erase(self, endereco, tamanho):
        assert (endereco, tamanho) == (FLASH_INICIO, 16)
        self.eventos.append('apagar')

    def flash(self, _endereco, _dados):
        self.eventos.append('gravar')
        if self.falha_flash:
            raise OSError(CHAVE_TESTE.hex())

    def verify(self, _endereco, _tamanho, _crc):
        self.eventos.append('verificar')

    def sw_reset(self, _modo):
        self.eventos.append('reiniciar')


@pytest.fixture
def estacao(tmp_path, monkeypatch):
    caminho_chave = tmp_path / 'somente-simulacao.hex'
    caminho_chave.write_text(CHAVE_TESTE.hex())
    monkeypatch.setenv('ASR_ARQUIVO_CHAVE_EEPROM', str(caminho_chave))
    caminho_firmware = tmp_path / 'producao.bin'
    firmware = struct.pack('<II', 0x20004000, FLASH_INICIO + 9) + bytes(8)
    caminho_firmware.write_bytes(firmware)
    manifesto = tmp_path / 'manifesto.json'
    manifesto.write_text(json.dumps(dict(mcu='ASR6601CB', otp_base=hex(BASE_TESTE), otp_formato=1,
                                         versao=900, sha256=hashlib.sha256(firmware).hexdigest())))
    param = SimpleNamespace(port='COM_TESTE', baud=115200, serial_producao=SERIAL_TESTE.hex(),
                            producao=manifesto, mcu='ASR6601CB',
                            addr_file=[hex(FLASH_INICIO), caminho_firmware])
    logs = []
    return param, SimpleNamespace(log=logs.append, apaga_eeprom=True), caminho_chave, logs


@pytest.mark.parametrize(('caso', 'esperado'), [
    ('vazio', 'OTP VAZIO'),
    ('incompleto', 'OTP INVÁLIDO/INCOMPLETO'),
    ('valido', 'OTP VÁLIDO, versão inicial 0900, quadro v1, ASR6601CB, flash 128 KiB, RAM 16 KiB'),
    ('outra_chave', 'OTP INCOMPATÍVEL — Incompatibilidade com a chave'),
    ('outro_mcu', 'OTP INCOMPATÍVEL — Variante registrada difere'),
    ('sem_chave', 'OTP NÃO VERIFICADA — Configure ASR_ARQUIVO_CHAVE_EEPROM'),
    ('falha_leitura', 'OTP NÃO VERIFICADA — Falha de comunicação'),
])
def test_flash_relata_otp_sem_impedir_gravacao(estacao, monkeypatch, capsys, caso, esperado):
    param, _, _, _ = estacao
    chave = CHAVE_TESTE[::-1] if caso == 'outra_chave' else CHAVE_TESTE
    mcu = 'ASR6601SE' if caso == 'outro_mcu' else 'ASR6601CB'
    registro = montar_registro(chave, 900, mcu, DATA_TESTE)
    if caso == 'vazio':
        registro = APAGADO
    if caso == 'incompleto':
        registro = registro[:88] + APAGADO[:8]
    if caso == 'sem_chave':
        monkeypatch.delenv('ASR_ARQUIVO_CHAVE_EEPROM')
    gravador = GravadorSimulado(registro)
    if caso == 'falha_leitura':
        gravador.falha_leitura = 1

    def apagar(endereco, tamanho):
        assert (endereco, tamanho) == (FLASH_INICIO, 16)
        assert gravador.leituras == 1
        assert esperado not in capsys.readouterr().out
        gravador.eventos.append('apagar')

    monkeypatch.setattr(gravador, 'erase', apagar)
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)
    assert cli.main(['-p', param.port, '--eeprom', 'flash', '--relatar-otp', '--mcu', 'ASR6601CB',
                     hex(FLASH_INICIO), str(param.addr_file[1])]) == 0
    saida = capsys.readouterr().out
    assert esperado in saida
    assert CHAVE_TESTE.hex() not in saida
    if caso == 'valido':
        assert '2026-11-18T09:30:00 (São Paulo)' in saida
    assert gravador.eventos[-4:] == ['apagar', 'gravar', 'verificar', 'reiniciar']
    assert gravador.unidades == []
    assert bytes(gravador.memoria) == registro


def test_vazio_e_repeticao_preservam_versao_inicial(estacao):
    param, config, _, logs = estacao
    gravador = GravadorSimulado()
    assert asr_flash(param, gravador, config)
    assert gravador.unidades == list(range(0, 96, 8))
    assert classificar_registro(bytes(gravador.memoria)) == ('VÁLIDO', 900)
    manifesto = json.loads(param.producao.read_text())
    param.producao.write_text(json.dumps(dict(manifesto, versao=901)))
    anterior = bytes(gravador.memoria)
    assert asr_flash(param, gravador, config)
    assert bytes(gravador.memoria) == anterior
    assert 'preservado, versão inicial 900' in logs[-2]
    assert logs[-1].endswith('versão 901')


@pytest.mark.parametrize('modo', ['outra_chave', 'incompleto', 'corrompido', 'experimental_72'])
def test_registro_recusado_sem_escrita(estacao, modo):
    param, config, _, _ = estacao
    memoria = bytearray(_montar_registro_teste(CHAVE_TESTE[::-1] if modo == 'outra_chave' else CHAVE_TESTE, 900))
    if modo == 'incompleto':
        memoria[88:] = APAGADO[:8]
    if modo == 'corrompido':
        memoria[56] ^= 1
    if modo == 'experimental_72':
        corpo = bytes(64)
        memoria = corpo + b'CONFOTP1' + b'\xff' * 24
    gravador = GravadorSimulado(memoria)
    with pytest.raises(CmdExcessao, match='Incompatibilidade|inválido ou incompleto'):
        asr_flash(param, gravador, config)
    assert not gravador.unidades and 'apagar' not in gravador.eventos


@pytest.mark.parametrize('dados', [None, 'invalido', 'aa' * 31, '00' * 32, 'FF' * 32])
def test_chave_invalida_antes_de_conectar(estacao, dados):
    param, config, caminho, _ = estacao
    if dados is None:
        caminho.unlink()
    else:
        caminho.write_text(dados)
    gravador = GravadorSimulado()
    with pytest.raises(CmdExcessao, match='Arquivo da chave'):
        asr_flash(param, gravador, config)
    assert not gravador.eventos


@pytest.mark.parametrize('etapa', range(1, 13))
def test_interrupcao_em_cada_unidade_bloqueia_repeticao(estacao, etapa):
    param, config, _, logs = estacao
    gravador = GravadorSimulado()
    gravador.falha_etapa = etapa
    param.producao_bin = True
    imagem, rodape = _montar_pacote_rodape(900)
    param.addr_file[1].write_bytes(imagem + rodape)
    with pytest.raises(CmdExcessao, match='Falha ao programar') as falha:
        asr_flash(param, gravador, config)
    assert CHAVE_TESTE.hex() not in (str(falha.value) + str(logs))
    with pytest.raises(CmdExcessao, match='inválido ou incompleto'):
        asr_flash(param, gravador, config)
    assert len(gravador.unidades) == etapa and 'apagar' not in gravador.eventos


@pytest.mark.parametrize('leitura', [1, 2, 3])
def test_falha_de_leitura_impede_gravacao(estacao, leitura, capsys):
    param, config, _, logs = estacao
    gravador = GravadorSimulado()
    gravador.falha_leitura = leitura
    with pytest.raises(CmdExcessao, match='Falha') as falha:
        asr_flash(param, gravador, config)
    assert 'apagar' not in gravador.eventos
    assert CHAVE_TESTE.hex() not in str(falha.value) + str(logs) + capsys.readouterr().out
    assert classificar_registro(bytes(gravador.memoria))[0] == (
        'VAZIO' if leitura == 1 else 'INVÁLIDO/INCOMPLETO' if leitura == 2 else 'VÁLIDO'
    )


def test_falha_flash_depois_da_otp_permite_repetir(estacao):
    param, config, _, _ = estacao
    gravador = GravadorSimulado()
    gravador.falha_flash = True
    with pytest.raises(CmdExcessao, match='OTP confirmada'):
        asr_flash(param, gravador, config)
    gravador.falha_flash = False
    assert asr_flash(param, gravador, config)
    assert len(gravador.unidades) == 12


@pytest.mark.parametrize('campo,valor', [('otp_formato', 2), ('otp_base', '0x10001E00'),
                                         ('mcu', 'ASR6601SE'), ('sha256', '0' * 64)])
def test_firmware_incompativel(estacao, campo, valor):
    param, config, _, _ = estacao
    manifesto = json.loads(param.producao.read_text())
    manifesto[campo] = valor
    param.producao.write_text(json.dumps(manifesto))
    gravador = GravadorSimulado()
    with pytest.raises(CmdExcessao, match='incompatível|divergente'):
        asr_flash(param, gravador, config)
    assert not gravador.eventos


@pytest.mark.parametrize('serial', [b'', bytes(8), b'\xff' * 8, bytes(range(8))])
def test_serial_inesperado_impede_acesso_a_otp(estacao, serial):
    param, config, _, _ = estacao
    gravador = GravadorSimulado()
    gravador.serial = serial
    with pytest.raises(CmdExcessao, match='Número de série'):
        asr_flash(param, gravador, config)
    assert gravador.leituras == 0 and not gravador.unidades


@pytest.mark.parametrize('base', ['0x10001D01', '0x10001BC0', '0x10001FC0'])
def test_reserva_invalida_impede_conexao(estacao, base):
    param, config, _, _ = estacao
    manifesto = json.loads(param.producao.read_text())
    param.producao.write_text(json.dumps(dict(manifesto, otp_base=base)))
    gravador = GravadorSimulado()
    with pytest.raises(CmdExcessao, match='reserva OTP'):
        asr_flash(param, gravador, config)
    assert not gravador.eventos


def test_flash_de_producao_pela_cli(estacao, monkeypatch, tmp_path, capsys):
    param, _, _, _ = estacao
    caminho_log = tmp_path / 'producao.log'
    gravador = GravadorSimulado()
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)
    assert cli.main(['-p', param.port, '--log-file', str(caminho_log), 'flash',
                     '--producao', str(param.producao), '--mcu', param.mcu,
                     *map(str, param.addr_file)]) == 0
    assert gravador.eventos[-4:] == ['gravar', 'verificar', 'reiniciar', 'fechar']
    assert gravador.unidades[-1] == 88
    log = caminho_log.read_text(encoding='utf-8')
    assert f'Produção ASR {SERIAL_TESTE.hex()}' in log
    assert 'versão inicial 900' in log and 'firmware gravado e verificado' in log
    assert CHAVE_TESTE.hex() not in log + capsys.readouterr().out


@pytest.mark.parametrize('caso, codigo, mensagem', [
    ('vazio', 0, 'OTP VAZIO'),
    ('valido', 0, 'OTP VÁLIDO, versão inicial 900'),
    ('incompleto', 1, 'OTP INVÁLIDO/INCOMPLETO'),
    ('outra_chave', 1, 'Incompatibilidade'),
    ('comunicacao', 1, 'Falha de comunicação'),
])
def test_somente_validar_nunca_grava(estacao, monkeypatch, capsys, caso, codigo, mensagem):
    param, _, _, _ = estacao
    memoria = APAGADO
    if caso in ('valido', 'incompleto', 'outra_chave'):
        chave = CHAVE_TESTE[::-1] if caso == 'outra_chave' else CHAVE_TESTE
        memoria = _montar_registro_teste(chave, 900)
    if caso == 'incompleto':
        memoria = memoria[:-8] + APAGADO[:8]
    gravador = GravadorSimulado(memoria)
    if caso == 'comunicacao':
        gravador.falha_leitura = 1
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)

    assert cli.main(['-p', param.port, 'flash', '--somente-validar',
                     '--producao', str(param.producao), '--mcu', param.mcu,
                     '--serial-producao', param.serial_producao, *map(str, param.addr_file)]) == codigo
    saida = capsys.readouterr()
    assert mensagem in saida.out + saida.err
    assert CHAVE_TESTE.hex() not in saida.out + saida.err
    assert 'Gravado com sucesso' not in saida.out
    assert gravador.eventos == ['porta', 'conectar', 'fechar']
    assert gravador.leituras == 1 and not gravador.unidades
    assert bytes(gravador.memoria) == memoria


def test_somente_validar_sem_producao_recusa_flash_legado(monkeypatch, capsys):
    gravador = GravadorSimulado()
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)
    assert cli.main(['-p', 'COM_TESTE', 'flash', '--somente-validar', '0x08000000', 'app.bin']) == 1
    assert 'Informe --producao' in capsys.readouterr().err
    assert not gravador.eventos


@pytest.mark.parametrize('modo, codigo, esperado', [
    ('candidata', 0, '0x10001DE0–0x10001E4F (112 bytes)'),
    ('ocupada', 0, 'Nenhuma faixa candidata'),
    ('leitura_curta', 1, 'Falha ao identificar o equipamento ou ler toda a OTP'),
])
def test_diagnosticar_otp_sem_arquivos(monkeypatch, capsys, modo, codigo, esperado):
    gravador = GravadorSimulado()
    memoria = bytearray(CHAVE_TESTE * 32)
    if modo == 'candidata':
        memoria[480:592] = b'\xff' * 112
    pedidos = []

    def ler_otp(endereco, tamanho):
        pedidos.append((endereco, tamanho))
        offset = endereco - 0x10001C00
        return bytes(memoria[offset:offset + tamanho - (modo == 'leitura_curta')])

    gravador.ler_otp = ler_otp
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)
    assert cli.main(['-p', 'COM_TESTE', 'diagnosticar_otp']) == codigo
    saida = capsys.readouterr()
    assert esperado in saida.out + saida.err
    assert CHAVE_TESTE.hex() not in saida.out + saida.err
    assert pedidos == [(0x10001C00, 512), (0x10001E00, 512)]
    assert gravador.eventos == ['porta', 'conectar', 'fechar']
    assert not gravador.unidades and gravador.sessao_reservada


@pytest.mark.parametrize('modo, esperado', [
    ('falha', 'leitura acima de 128 KiB falhou'),
    ('espelho', 'leituras iguais'),
    ('apagada', 'retornou apenas FF'),
    ('distinta', 'leituras distintas'),
])
def test_sondar_flash_sem_escritas(monkeypatch, capsys, modo, esperado):
    gravador = GravadorSimulado()
    enderecos = []

    def ler_reg(endereco):
        enderecos.append(endereco)
        if endereco < 0x08020000 or modo == 'espelho':
            return (0x12345678,)
        if modo == 'falha':
            raise CmdExcessao('Falha simulada')
        return (0xFFFFFFFF if modo == 'apagada' else 0xABCDEF01,)

    monkeypatch.setattr(gravador, 'ler_reg', ler_reg)
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)
    assert cli.main(['-p', 'COM_TESTE', 'diagnosticar_flash_asr']) == 0
    saida = capsys.readouterr().out
    assert esperado in saida and 'Variante não confirmada' in saida
    assert '12345678' not in saida
    assert enderecos[:6] == [0x08000000, 0x08000004, 0x08000008, 0x08000100, 0x08001000, 0x08020000]
    assert gravador.eventos == ['porta', 'conectar', 'fechar']
    assert not gravador.unidades and gravador.leituras == 0


@pytest.mark.parametrize('modo,codigo,mensagem', [
    ('independente', 0, 'compatível com ASR6601SE'),
    ('ocupada', 1, 'antes da escrita'),
    ('fora_da_faixa', 1, 'antes da escrita'),
    ('espelhada', 1, 'Ensaio inconclusivo'),
    ('falha_escrita', 1, 'Ensaio inconclusivo'),
    ('serial_errado', 1, 'Número de série diferente'),
])
def test_ensaio_opt_in_de_escrita(monkeypatch, capsys, modo, codigo, mensagem):
    gravador = GravadorSimulado()
    apagada = b'\xff' * 4096
    inferior, superior = 0x08002000, 0x08022000
    paginas = {inferior: bytearray(apagada), superior: bytearray(apagada)}
    if modo == 'espelhada':
        paginas[superior] = paginas[inferior]
    if modo == 'ocupada':
        paginas[inferior][100] = 0
    escritas = []
    apagamentos = []

    def verificar(endereco, tamanho, crc):
        if modo == 'fora_da_faixa' and endereco == superior:
            raise CmdExcessao('Endereço inválido')
        if zlib.crc32(paginas[endereco][:tamanho]) != crc:
            raise CmdExcessao('CRC diferente')

    def gravar(endereco, dados):
        escritas.append(endereco)
        assert endereco == superior and len(dados) == 8
        if modo == 'falha_escrita':
            raise OSError
        paginas[endereco][:len(dados)] = dados

    def apagar(endereco, tamanho):
        apagamentos.append(endereco)
        assert endereco == superior and tamanho == 4096
        paginas[endereco][:] = apagada

    gravador.verify = verificar
    gravador.flash = gravar
    gravador.erase = apagar
    monkeypatch.setattr(cli, 'ASRLoader', lambda config: gravador)
    serial = '0102030405060708' if modo == 'serial_errado' else SERIAL_TESTE.hex()
    assert cli.main(['-p', 'COM_TESTE', 'diagnosticar_flash_asr', '--testar-escrita', serial]) == codigo
    saida = capsys.readouterr()
    assert mensagem in saida.out + saida.err
    assert escritas == ([superior] if modo in ('independente', 'espelhada', 'falha_escrita') else [])
    assert apagamentos == ([superior] if modo == 'independente' else [])
    if modo == 'independente':
        assert all(pagina == apagada for pagina in paginas.values())
    assert not gravador.unidades and gravador.leituras == 0


def _montar_pacote_rodape(versao, variante_boot=0):
    """Cria uma imagem com dois vetores e o rodapé binário de 70 bytes."""
    imagem = bytearray(0x2010)
    struct.pack_into('<II', imagem, 0, 0x20004000, FLASH_INICIO + 9)
    struct.pack_into('<II', imagem, 0x2000, 0x20004000, FLASH_INICIO + 0x2009)
    imagem[8] = variante_boot
    rodape = struct.pack('<8sHHIHBBIHII32s', b'ASRPROD\0', 1, 70, len(imagem), versao,
                         1, variante_boot, BASE_TESTE, 1, FLASH_INICIO, FLASH_INICIO + 0x2000,
                         hashlib.sha256(imagem).digest())
    return bytes(imagem), rodape + struct.pack('<I', zlib.crc32(rodape))


def test_previa_otp_pela_cli_oculta_chave_e_exibe_pacote_completo_quando_solicitado(estacao, monkeypatch, capsys):
    param, _, _, _ = estacao
    caminho = param.addr_file[1]
    imagem, rodape = _montar_pacote_rodape(900)
    caminho.write_bytes(imagem + rodape)

    def recusar_conexao(*_args, **_kwargs):
        pytest.fail('A prévia deve funcionar sem acessar a porta serial')

    monkeypatch.setattr(cli, 'ASRLoader', recusar_conexao)
    argumentos = ['otp_producao_inspect', str(caminho), '--mcu', 'ASR6601CB']
    assert cli.main(argumentos) == 0
    saida = capsys.readouterr().out
    assert 'Versão inicial (BCD)' in saida
    assert '0x10001C08  XX XX XX XX XX XX XX XX' in saida
    assert saida.count(' XX') == 32
    assert '01 02 03 04 05 06 07 08' not in saida

    assert cli.main([*argumentos, '--exibir-chave']) == 0
    saida = capsys.readouterr().out
    linhas_pacote = [linha for linha in saida.splitlines() if linha.startswith('0x10001C')]
    pacote = bytes.fromhex(' '.join(linha.split(maxsplit=1)[1] for linha in linhas_pacote))
    assert len(linhas_pacote) == 12
    assert pacote[8:40] == CHAVE_TESTE
    assert classificar_registro(pacote) == ('VÁLIDO', 900)


@pytest.mark.parametrize('variante_boot', (0, 1))
def test_rodape_provisiona_bcd_e_grava_somente_imagem(estacao, variante_boot):
    """Confere o conteúdo OTP e a faixa exata escrita na flash simulada."""
    param, config, _, _ = estacao
    param.producao_bin = True
    param.producao = None
    imagem, rodape = _montar_pacote_rodape(900, variante_boot)
    param.addr_file[1].write_bytes(imagem + rodape)
    gravador = GravadorSimulado()
    blocos = []
    gravador.erase = lambda endereco, tamanho: blocos.append((endereco, tamanho))
    gravador.flash = lambda endereco, dados: blocos.append((endereco, dados))
    gravador.verify = lambda endereco, tamanho, crc: blocos.append((endereco, tamanho, crc))
    assert asr_flash(param, gravador, config)
    assert gravador.memoria[:2] == b'\x01\x60'
    assert gravador.memoria[2:4] == b'\x00\x09'
    assert classificar_registro(bytes(gravador.memoria)) == ('VÁLIDO', 900)
    assert blocos[0] == (FLASH_INICIO, len(imagem))
    assert blocos[1:-1] == [(FLASH_INICIO + i, imagem[i:i + 512]) for i in range(0, len(imagem), 512)]
    assert blocos[-1] == (FLASH_INICIO, len(imagem), zlib.crc32(imagem))

    imagem, rodape = _montar_pacote_rodape(901, variante_boot)
    param.addr_file[1].write_bytes(imagem + rodape)
    registro = bytes(gravador.memoria)
    assert asr_flash(param, gravador, config)
    assert gravador.memoria == registro


@pytest.mark.parametrize('alteracao',
                         ('imagem', 'rodape', 'truncado', 'mcu', 'versao', 'otp', 'formato_otp', 'variante_boot'))
def test_rodape_invalido_interrompe_antes_da_conexao(estacao, alteracao):
    """Recusa corrupção e metadados incompatíveis sem abrir a sessão serial."""
    param, config, _, _ = estacao
    param.producao_bin = True
    imagem, rodape = _montar_pacote_rodape(10000 if alteracao == 'versao' else 900)
    if alteracao == 'mcu':
        param.mcu = 'ASR6601SE'
    if alteracao == 'otp':
        corpo = rodape[:20] + struct.pack('<I', BASE_TESTE + 8) + rodape[24:-4]
        rodape = corpo + struct.pack('<I', zlib.crc32(corpo))
    if alteracao == 'formato_otp':
        corpo = rodape[:24] + b'\x03\x00' + rodape[26:-4]
        rodape = corpo + struct.pack('<I', zlib.crc32(corpo))
    if alteracao == 'variante_boot':
        corpo = rodape[:19] + b'\x02' + rodape[20:-4]
        rodape = corpo + struct.pack('<I', zlib.crc32(corpo))
    if alteracao == 'imagem':
        imagem = bytes([imagem[0] ^ 1]) + imagem[1:]
    if alteracao == 'rodape':
        rodape = rodape[:-1] + bytes([rodape[-1] ^ 1])
    if alteracao == 'truncado':
        rodape = rodape[:-1]
    param.addr_file[1].write_bytes(imagem + rodape)
    gravador = GravadorSimulado()
    with pytest.raises(CmdExcessao, match='Binário de produção inválido'):
        asr_flash(param, gravador, config)
    assert gravador.eventos == []
