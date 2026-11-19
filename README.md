# ASR Loader

`ASR_Loader: v{{BUILD_VERSION}}`
`{{BUILD_DATE}}`

Ferramenta para gravação e debug de microcontroladores ASR via porta serial.

---

## Sumário

- [ASR Loader](#asr-loader)
    - [Ambiente de desenvolvimento](#ambiente-de-desenvolvimento)
    - [Criar o novo .exe](#criar-o-novo-exe)
    - [Substituir o asr_loader.exe em projetos com ASR:](#substituir-o-asr_loaderexe-em-projetos-com-asr)
- [Uso](#uso)
- [Parâmetros globais](#parâmetros-globais)
    - [COM PORT: -p ou --port](#com-port--p-ou---port)
    - [Baudrate: -b ou --baud](#baudrate--b-ou---baud)
    - [Modo log verboso: -v ou --verbose](#modo-log-verboso--v-ou---verbose)
    - [Salvar log em arquivo: --log-file](#salvar-log-em-arquivo---log-file)
    - [Salvar trace estruturado: --trace-json](#salvar-trace-estruturado---trace-json)
    - [Timeout de conexão: -t ou --timeout](#timeout-de-conexão--t-ou---timeout)
    - [Boot automático via DTR/RTS: --no-auto-boot](#boot-automático-via-dtrrts---no-auto-boot)
    - [Tempos do boot automático: --boot-reset-delay e --boot-release-delay](#tempos-do-boot-automático---boot-reset-delay-e---boot-release-delay)
    - [Manter EEPROM: -e ou --eeprom](#manter-eeprom--e-ou---eeprom)
    - [Firmware v8: --v8](#firmware-v8---v8)
    - [Help: -h ou --help](#help--h-ou---help)
- [Comandos](#comandos)
    - [make](#make)
    - [erase](#erase)
    - [flash](#flash)
        - [Gravação de produção PR439v3](#gravação-de-produção-pr439v3)
    - [producao_inspect](#producao_inspect)
    - [otp_producao_inspect](#otp_producao_inspect)
    - [bin_inspect](#bin_inspect)
    - [bin_extrair](#bin_extrair)
    - [bin_empacotar](#bin_empacotar)
    - [make validar_bin](#make-validar_bin)
    - [prevalidar](#prevalidar)
    - [firmware_inspect](#firmware_inspect)
    - [verify](#verify)
    - [reset](#reset)
    - [hw_reset](#hw_reset)
    - [dtr1 / dtr0 / rts1 / rts0](#dtr1--dtr0--rts1--rts0)
    - [clear_eeprom](#clear_eeprom)
    - [identificar_mcu](#identificar_mcu)
    - [mapa_flash](#mapa_flash)
    - [mapa_sram](#mapa_sram)
    - [mapa_eeprom](#mapa_eeprom)
    - [mapa_memoria](#mapa_memoria)
    - [serial](#serial)
    - [comdiag](#comdiag)
    - [doctor](#doctor)
    - [testeboot](#testeboot)
    - [ota_pack](#ota_pack)
    - [ota_pack_verify](#ota_pack_verify)
    - [ota_pack_inspect](#ota_pack_inspect)
    - [ota_cript](#ota_cript)
    - [ota_cript_verify](#ota_cript_verify)
    - [jump](#jump)
    - [versao_bootloader](#versao_bootloader)
    - [diagnosticar_otp](#diagnosticar_otp)
    - [diagnosticar_flash_asr](#diagnosticar_flash_asr)
    - [ler_otp](#ler_otp)
    - [escrever_otp](#escrever_otp)
    - [ler_opt0](#ler_opt0)
    - [escrever_opt0](#escrever_opt0)
    - [ler_opt1](#ler_opt1)
    - [escrever_opt1](#escrever_opt1)
    - [ler_reg](#ler_reg)
    - [escrever_reg](#escrever_reg)
    - [ler_mem](#ler_mem)
    - [snapshot](#snapshot)
    - [help](#help)
    - [versao](#versao)
- [Observações](#observações)
- [Exemplo de flash.bat](#exemplo-de-flashbat)

---

## ASR Loader

O `ASR Loader` é uma ferramenta de linha de comando para gravação e debug de microcontroladores ASR via porta serial.
Ele suporta uma variedade de comandos para interagir com o bootloader dos microcontroladores ASR, permitindo operações
como gravação de firmware, leitura/escrita de memória, controle de boot e geração de pacotes OTA.
A ferramenta é projetada para ser fácil de usar, com uma interface de linha de comando intuitiva e opções de
configuração flexíveis.
Ela é especialmente útil para desenvolvedores que trabalham com microcontroladores ASR, oferecendo uma solução eficiente
para gerenciamento de firmware e depuração.

### Ambiente de desenvolvimento

1. Certifique-se de ter o Python 3.x instalado em seu sistema.
2. Clone ou baixe este repositório para o seu ambiente local.
3. Navegue até a pasta do projeto no terminal.
4. Instale as dependências necessárias usando o comando:

```powershell
pip install -r requirements.txt
```

Para executar os testes automatizados sem hardware:

```powershell
py -m unittest discover -s tests
```

---

### Criar o novo .exe

```bat
build.bat
```

ou

```powershell
pyinstaller --onefile asr_loader.py
```

ou

```powershell
py -m PyInstaller --onefile asr_loader.py
```

---

### Substituir o asr_loader.exe em projetos com ASR:

Este script realiza um build e copia automaticamente o executável versionado mais recente de `dist\_loader-v*.exe` para
as pastas de tools dos projetos com ASR.
Também gera um arquivo `MANUAL_asr_loader.md` com a versão e a data do último executável encontrado em `dist`,
preenchidas automaticamente a partir do `README.md`.

```bat
atualizar-builds.bat
```

---

## Uso

Execute o script via terminal:

```powershell
py asr_loader.py <comando> [opções][argumentos]
```

ou

```powershell
.\asr_loader.exe <comando> [opções][argumentos]
```

ou

```powershell
make <comando> [opções][argumentos]
```

---

## Parâmetros globais

### COM PORT: -p ou --port

Configura a porta serial.
Caso não seja passado nada, lista as portas seriais disponíveis e tenta conectar na primeira que encontrar o
dispositivo.

**Formato:**

```text
-p <porta_serial>
--port <porta_serial>
```

**Exemplo:**

```powershell
make -p COM3 flash 0x08000000 app.bin
```

---

### Baudrate: -b ou --baud

Configura o baudrate.
Por padrão vem com 921600, caso não seja passado nada.

**Formato:**

```text
-b <baudrate>
--baud <baudrate>
```

**Exemplo:**

```powershell
make -b 115200 flash 0x08000000 app.bin
```

---

### Modo log verboso: -v ou --verbose

Configura modo verboso. Mostra todos os dados trafegados pela serial.

**Formato:**

```text
-v
--verbose
```

**Exemplo:**

```powershell
make -v flash 0x08000000 app.bin
```

---

### Salvar log em arquivo: --log-file

Salva em arquivo os principais eventos da execução, incluindo porta usada, parâmetros de conexão, sequência `DTR/RTS`,
pacotes `TX/RX` e erros.

**Formato:**

```text
--log-file <arquivo.log>
```

**Exemplo:**

```powershell
python asr_loader.py -p COM3 --log-file debug_gravacao.log testeboot
```

Esse log é indicado para depurar bancada, timing de auto boot e falhas intermitentes de comunicação.

---

### Salvar trace estruturado: --trace-json

Salva eventos estruturados em JSON Lines (`.jsonl`) para análise automática em scripts.
O trace inclui eventos como `serial_tx` e `serial_result`, com comando, tamanho de pacote, status, duração e erro quando
houver.

**Formato:**

```text
--trace-json <arquivo.jsonl>
```

**Exemplo:**

```powershell
python asr_loader.py -p COM3 --trace-json trace_testeboot.jsonl testeboot --json
```

Use junto com `--log-file` quando precisar comparar falhas entre placas, cabos, portas COM ou ajustes de auto boot.

---

### Timeout de conexão: -t ou --timeout

Configura o timeout em segundos. Padrão é 2 segundos.

**Estrutura:**

```text
-t <segundos>
--timeout <segundos>
```

**Formato:**

```powershell
make -t 10 flash 0x08000000 app.bin
```

---

### Boot automático via DTR/RTS: --no-auto-boot

Por padrão, antes de conectar no bootloader, o ASR Loader aciona as linhas de controle da serial para colocar o MCU em
modo de gravação.

A sequência padrão é:

1. ativa `DTR`;
2. ativa `RTS`;
3. aguarda `--boot-reset-delay`;
4. libera `RTS`;
5. aguarda `--boot-release-delay`;
6. libera `DTR`;
7. limpa os buffers da serial;
8. envia o comando de sincronismo para o bootloader.

Use a ligação de hardware correspondente ao seu circuito:

- `RTS`: linha usada para reset do MCU;
- `DTR`: linha usada para selecionar modo boot/gravação.

Se o seu hardware já coloca o ASR manualmente em modo boot, ou se você estiver depurando a conexão, desative o
acionamento automático:

**Formato:**

```text
--no-auto-boot
```

**Exemplo:**

```powershell
make --no-auto-boot -p COM3 flash 0x08000000 app.bin
```

---

### Tempos do boot automático: --boot-reset-delay e --boot-release-delay

Configura os tempos da sequência automática de entrada no bootloader.
Os valores são em segundos e o padrão é `0.1` para ambos.

**Formato:**

```text
--boot-reset-delay <segundos>
--boot-release-delay <segundos>
```

**Exemplo:**

```powershell
make --boot-reset-delay 0.2 --boot-release-delay 0.2 -p COM3 flash 0x08000000 app.bin
```

---

### Manter EEPROM: -e ou --eeprom

Mantém os dados da EEPROM ao apagar a flash.

**Formato:**

```text
-e
--eeprom
```

**Exemplo:**

```powershell
make -e flash 0x08000000 app.bin
```

---

### Help: -h ou --help

Mostra a ajuda com todos os comandos e opções.

**Formato:**

```text
-h
--help
```

**Exemplo:**

```powershell
make -h
```

---

## Comandos

### make

O comando `make` é um atalho para executar o script com os parâmetros globais de forma mais simples. Ele é especialmente
útil para quem está acostumado a usar o `make` em projetos de firmware e deseja uma sintaxe mais concisa para os
comandos de gravação e debug. **Formato:**

```text
make <comando> [opções] [argumentos]
```

**Exemplo:**

```powershell
make flash 0x08000000 app.bin
```

Este comando é equivalente a:

```powershell
python asr_loader.py flash 0x08000000 app.bin
```

O `make` é apenas um atalho e não tem funcionalidades adicionais além de simplificar a execução dos comandos do
`asr_loader.py` com os parâmetros globais.
Quando você usa `make`, ele automaticamente passa os parâmetros globais configurados para o comando que você deseja
executar, tornando a linha de comando mais limpa e fácil de usar.

---

### erase

Apaga uma área da flash a partir de um endereço específico.

**Formato:**

```text
erase <endereço_inicial> <tamanho_em_bytes>
```

**Exemplo:**

```powershell
python asr_loader.py erase 0x08000000 4096
```

Apaga 4096 bytes a partir do endereço 0x08000000.

---

### flash

Apaga e grava arquivos na flash.
Antes de conectar no hardware, o comando executa uma pré-validação local do plano de gravação para validar arquivos,
tamanhos, CRC32, endereços e overlaps.

**Formato:**

```text
flash <endereço_inicial> <arquivo.bin>
```

**Exemplo:**

```powershell
python asr_loader.py flash 0x08000000 app.bin
```

Grava o arquivo `app.bin` no endereço 0x08000000.

Para a aplicação do PR439v3, `flash --eeprom-ab --mcu ASR6601SE` apaga e
verifica os 8 KiB da EEPROM emulada antes de gravar a aplicação. Use a opção
global `--eeprom` para preservar as duas páginas.

Para gravar com conferência da OTP do PR439v3, use `flash --relatar-otp --mcu ASR6601SE`
ou indique `ASR6601CB` conforme a placa. O gravador lê o quadro de 96 bytes antes
de apagar a flash e informa o estado no fim. Se o quadro estiver válido, confere o
modelo e a chave indicada por `ASR_ARQUIVO_CHAVE_EEPROM` e exibe apenas
`OTP VÁLIDO` quando tudo confere. OTP vazia, inválida,
incompatível ou cuja leitura ou chave não pôde ser conferida gera um aviso e
permite a gravação. A opção apenas lê a OTP.

#### Gravação de produção PR439v3

Use `flash --producao-bin` com o binário combinado que contém os metadados
ASRPROD. Informe a porta e a variante conferida na placa. O gravador lê o
serial automaticamente, confirma ou provisiona o quadro OTP v1 de 96 bytes
e grava apenas a imagem extraída do arquivo, preservando as páginas da EEPROM.

```powershell
$env:ASR_ARQUIVO_CHAVE_EEPROM = Read-Host 'Caminho do arquivo da chave da EEPROM'
.\asr_loader.exe -p COM3 flash --producao-bin --mcu ASR6601SE 0x08000000 .\producao.bin
```

- `--mcu ASR6601CB|ASR6601SE` é obrigatório no modo de produção.
- `--serial-producao SERIAL_HEX` é opcional. Informe 16 dígitos hexadecimais
  para exigir que o serial lido coincida com o da unidade esperada.
- `--somente-validar` classifica a OTP e confere a chave sem programar a OTP
  ou apagar ou gravar a flash. Requer o binário, a variante e o caminho da chave.
- `--producao MANIFESTO` seleciona o fluxo legado com JSON e binário sem metadados.
  Use apenas um modo de produção por vez.

```powershell
.\asr_loader.exe -p COM3 flash --producao-bin --somente-validar --mcu ASR6601SE 0x08000000 .\producao.bin
```

Consulte o [procedimento de produção e o mapa OTP](docs/provisionamento-eeprom.md).

---

### producao_inspect

Valida offline um combinado de produção PR439v3. Confere os metadados, o
SHA-256, a variante, as origens, os vetores de reset e os limites da imagem.
Requer `--mcu` e dispensa porta serial e chave.

```powershell
.\asr_loader.exe producao_inspect .\producao.bin --mcu ASR6601SE
```

### otp_producao_inspect

Mostra a tabela de campos e os 96 bytes, em hexadecimal, do quadro que
seria gravado em uma OTP vazia. Usa o mesmo binário ASRPROD, a mesma variante
e a mesma chave da EEPROM da gravação de produção. Funciona sem porta
serial. A data/hora e o CRC são recalculados na gravação.

```powershell
$env:ASR_ARQUIVO_CHAVE_EEPROM = Read-Host 'Caminho do arquivo da chave da EEPROM'
.\asr_loader.exe otp_producao_inspect .\producao.bin --mcu ASR6601SE
```

A chave aparece como `XX` por padrão. Use `--exibir-chave` para ver o
pacote completo, incluindo a chave da EEPROM.

### bin_inspect

Valida os metadados ASRPROD e a integridade do conteúdo. Exibe todos os campos
dos metadados em uma tabela com offset, tamanho e valor, incluindo SHA-256 e
CRC-32. Informa também a quantidade de bytes após extração.

```powershell
.\asr_loader.exe bin_inspect .\producao.bin
```

### bin_extrair

Salva em outro arquivo o conteúdo sem os metadados. Para OTA, preserva a marca
final `TCHE` do pacote original. Se a saída já existir, será substituída.

```powershell
.\asr_loader.exe bin_extrair .\producao.bin .\imagem-gravavel.bin
```

### bin_empacotar

Acrescenta os metadados ASRPROD e a marca final `TCHE` ao arquivo de entrada.
Informe a entrada, a saída, a versão decimal do firmware, o código do MCU,
o tipo do binário, a origem da imagem e a origem da aplicação, nessa ordem.
O arquivo de entrada precisa estar sem metadados. A saída existente será substituída.

```powershell
.\asr_loader.exe bin_empacotar .\imagem-gravavel.bin .\producao.bin 900 2 0 0x08000000 0x08002000
```

| Parâmetro     | Valores                                                                                                                         |
|---------------|---------------------------------------------------------------------------------------------------------------------------------|
| Versão        | Inteiro decimal de `0` a `9999`                                                                                                 |
| Código do MCU | `1` para ASR6601CB ou `2` para ASR6601SE                                                                                        |
| Tipo          | `0` produção normal, `1` produção cripto, `2` aplicação, `3` bootloader, `4` bootloader cripto, `5` OTA simples, `6` OTA cripto |
| Origens       | Endereços de memória de acordo com a linkedição do binário                                                                      |

### make validar_bin

No repositório do firmware PR439v3, o alvo `validar_bin` chama `bin_inspect`
com o arquivo escolhido em `BIN`. A validação é offline.

```powershell
make validar_bin BIN="release/pr439v3-postyou-dlms_producao.bin"
```

---

### prevalidar

Valida localmente um plano de gravação sem abrir a porta serial.
É útil para checar argumentos de `flash` em scripts antes de chegar na bancada.

**Formato:**

```text
prevalidar <endereço_inicial> <arquivo.bin> [<endereço_inicial> <arquivo.bin> ...] [--strict-app-range] [--json]
```

**Exemplo:**

```powershell
python asr_loader.py prevalidar 0x08000000 app.bin
python asr_loader.py prevalidar 0x08000000 app.bin --json
```

Valida:

- arquivo existente e legível;
- tamanho e CRC32;
- endereço inicial/final;
- overlap entre múltiplos arquivos;
- aviso para endereços fora da faixa padrão da aplicação (`0x08000000` a `0x08040000`).

Com `--strict-app-range`, endereço fora da faixa da aplicação vira erro.

---

### firmware_inspect

Inspeciona localmente firmware raw ou pacote OTA simples.
O comando valida a estrutura inicial da aplicação e ajuda a detectar firmware desalinhado antes da gravação.

**Formato:**

```text
firmware_inspect <arquivo.bin> [--base-address <endereço>] [--strict] [--json]
```

**Exemplo:**

```powershell
python asr_loader.py firmware_inspect app.bin
python asr_loader.py firmware_inspect app_ota.bin --json
```

Valida:

- tamanho e CRC32;
- detecção de pacote OTA simples quando o header é válido;
- `MSP` dentro da SRAM;
- `Reset_Handler` com bit Thumb setado;
- `Reset_Handler` apontando para a faixa esperada da aplicação.

Com `--strict`, falhas estruturais retornam código de saída `1`.

---

### verify

Verifica o conteúdo da flash comparando com um arquivo.

**Formato:**

```text
verify <endereço_inicial> <arquivo.bin>
```

**Exemplo:**

```powershell
python asr_loader.py verify 0x08000000 app.bin
```

Verifica se o conteúdo da flash a partir de 0x08000000 é igual ao arquivo `app.bin`.
Retorna "Verificacao completa! Flash igual ao arquivo." se for igual,
ou "ERROR: flash diferente do arquivo" se houver diferença.

---

### reset

Reinicia o dispositivo.
Este comando usa o comando de reset do bootloader, portanto precisa conseguir conectar no ASR antes.

**Formato:**

```text
reset
```

**Exemplo:**

```powershell
python asr_loader.py reset
```

Reinicia o dispositivo conectado.

---

### hw_reset

Reinicia o dispositivo via linha de hardware `RTS`, sem precisar sincronizar com o bootloader.

**Formato:**

```text
hw_reset [--boot]
```

**Exemplo de reset normal:**

```powershell
python asr_loader.py -p COM3 hw_reset
```

**Exemplo de reset entrando no bootloader:**

```powershell
python asr_loader.py -p COM3 hw_reset --boot
```

No modo normal, o comando apenas pulsa `RTS`.
Com `--boot`, o comando ativa `DTR`, pulsa `RTS` e depois libera `DTR`, usando os tempos configurados por
`--boot-reset-delay` e `--boot-release-delay`.

---

### dtr1 / dtr0 / rts1 / rts0

Controla diretamente as linhas `DTR` e `RTS` da porta serial para teste de hardware.

**Formato:**

```text
dtr1 [--hold <segundos>]
dtr0 [--hold <segundos>]
rts1 [--hold <segundos>]
rts0 [--hold <segundos>]
```

**Exemplos:**

```powershell
python asr_loader.py -p COM3 dtr1
python asr_loader.py -p COM3 dtr0
python asr_loader.py -p COM3 rts1 --hold 5
python asr_loader.py -p COM3 rts0 --hold 5
```

Sem `--hold`, o comando mantém a porta aberta e a linha no estado selecionado até `Ctrl+C`.
Com `--hold`, mantém pelo tempo informado e fecha a porta ao final.

Observação: em adaptadores como CP2102 e nos circuitos de reset/boot com transistor, o nível elétrico medido no pino do
MCU pode ficar invertido em relação ao estado lógico enviado pelo software. Para validar, meça diretamente no pino`DTR`/
`RTS` do CP2102 e depois no ponto do circuito que chega ao MCU.

---

### clear_eeprom

Apaga a EEPROM emulada da variante informada. No ASR6601SE, apaga as duas
páginas físicas de `0x0803E000` a `0x0803FFFF` (8 KiB), inclusive com `--v8`.
No ASR6601CB, apaga a última página física (4 KiB).

**Formato:**

```text
clear_eeprom --mcu {ASR6601CB,ASR6601SE}
```

**Exemplo:**

```powershell
python asr_loader.py -p COM9 clear_eeprom --mcu ASR6601SE
```

---

### serial

Lê o número de série do microcontrolador.
O número de série é um identificador único atribuído a cada microcontrolador durante o processo de fabricação.
Ele é usado para identificar individualmente cada dispositivo, permitindo rastreamento, autenticação e controle de
qualidade.

**Formato:**

```text
serial
```

**Exemplo:**

```powershell
python asr_loader.py serial
```

Retorna o número de serial do dispositivo com 16 bytes.
Exemplo de saída: `0123456789abcdef`

---

### comdiag

Mostra informações úteis para desenvolvimento e depuração sem conectar no bootloader.
Inclui versão do ASR Loader, data/fonte do build, Python em uso, versão do `pyserial` e detalhes das portas seriais
detectadas.

**Formato:**

```text
comdiag [--json]
```

**Exemplo:**

```powershell
python asr_loader.py comdiag
```

**Exemplo em JSON:**

```powershell
python asr_loader.py comdiag --json
```

Use esse comando ao abrir um reporte de problema de gravação, porta COM ou driver USB-serial.

---

### doctor

Executa um diagnóstico guiado do ambiente e, opcionalmente, testa sincronismo com o bootloader.

**Formato:**

```text
doctor [--testeboot] [--json]
```

**Exemplo:**

```powershell
python asr_loader.py -p COM3 doctor
python asr_loader.py -p COM3 doctor --testeboot --json
```

O relatório inclui:

- versão do ASR Loader, Python e `pyserial`;
- portas seriais detectadas;
- porta selecionada;
- configuração de auto boot;
- resultado opcional do `testeboot`;
- recomendações objetivas para o próximo teste de bancada.

---

### testeboot

Testa entrada no bootloader e sincronismo sem apagar, gravar ou alterar memória flash.
É o primeiro comando recomendado para validar o circuito de auto boot e a comunicação serial.

**Formato:**

```text
testeboot [--json]
testeboot --sweep [--sweep-bauds <lista>] [--sweep-reset-delays <lista>] [--sweep-release-delays <lista>] [--json]
```

**Exemplo:**

```powershell
python asr_loader.py -p COM3 testeboot
```

**Exemplo de sweep de timings:**

```powershell
python asr_loader.py -p COM3 testeboot --sweep --sweep-bauds 115200,921600 --sweep-reset-delays 0.05,0.1,0.2 --sweep-release-delays 0.05,0.1,0.2
```

**Exemplo com log:**

```powershell
python asr_loader.py -p COM3 --log-file testeboot.log testeboot
```

Retorna código de saída `0` se o bootloader responder e `1` se houver falha.
Com `--sweep`, testa combinações de baudrate e delays de `DTR/RTS`, imprimindo uma tabela `OK/FAIL`.

---

### ota_pack

Gera um pacote OTA com header de 16 bytes e concatena com o firmware `.bin`.
Use esse arquivo para gravação na flash externa a partir do endereço `0x00000000`.

**Formato:**

```text
ota_pack <arquivo_firmware.bin> [arquivo_saida.bin]
```

**Exemplo:**

```powershell
python asr_loader.py ota_pack app.bin app_ota.bin
```

Se `arquivo_saida.bin` não for informado, o nome padrão será `<arquivo_firmware>_ota.bin`.

#### O que o firmware/bootloader precisa implementar

Para que o `ota_pack` funcione no bootloader do firmware, o bootloader precisa ler o pacote OTA da flash externa,
validar o header e a integridade do firmware, e só então aceitar a imagem.

O formato gerado pela ferramenta é:

```text
+-------------------------------+
| Header OTA (16 bytes)         |
+-------------------------------+
| Firmware bruto (N bytes)      |
+-------------------------------+
```

#### Header OTA (16 bytes)

Todos os campos são `little-endian`.

```text
Offset  Tamanho  Campo
0x00    4        magic      = 0xB00710AD
0x04    4        size       = tamanho do firmware em bytes
0x08    4        crc32      = CRC32 IEEE do firmware bruto
0x0C    4        reserved   = 0x00000000
```

#### Estruturas mínimas no bootloader

Uma implementação equivalente em C pode usar algo nesta linha:

```c
typedef struct {
    uint32_t magic;
    uint32_t size;
    uint32_t crc32;
    uint32_t reserved;
} ota_header_t;
```

#### Sequência de validação recomendada no bootloader

Ao encontrar um pacote OTA simples na flash externa, o bootloader deve:

1. ler o `header` nos primeiros 16 bytes;
2. validar `magic == 0xB00710AD`;
3. validar `reserved == 0x00000000`;
4. validar se `size` é compatível com o espaço disponível na flash externa e com o destino na flash interna;
5. ler os `size` bytes de firmware bruto logo após o header;
6. calcular o `CRC32` do firmware bruto;
7. comparar o `CRC32` calculado com o campo `crc32` do header;
8. somente se tudo passar, aceitar a imagem para gravação/execução.

#### Fluxo prático sugerido no firmware

Fluxo típico no bootloader:

1. bootloader inicia;
2. detecta pacote OTA na flash externa em `0x00000000`;
3. lê o `header` e valida `magic`, `size`, `crc32` e `reserved`;
4. se a validação falhar, aborta o update e mantém o firmware atual;
5. se a validação passar, grava/copia o firmware para a flash de execução;
6. opcionalmente grava estado de sucesso e limpa a imagem OTA consumida.

#### Observações importantes

- todos os inteiros usados no pacote estão em `little-endian`;
- o `CRC32` usado aqui é o IEEE (`binascii.crc32` no Python);
- o firmware dentro do pacote é bruto, sem trailer de autenticação;
- o `ota_pack` verifica a integridade com CRC32. Para autenticação e criptografia, use `ota_cript`.

#### Inspeção estrutural no MCU antes da gravação

Para deixar o mesmo critério do bootloader visível no LOG antes de gravar, use `ota_pack_inspect`.

Esse comando mostra:

- header OTA já validado;
- `CRC32` do firmware;
- primeiros 64 bytes da `vector table`;
- `MSP`, `Reset_Handler`, `NMI` e `HardFault`;
- se o `Reset_Handler` está com Thumb setado;
- se os handlers caem na faixa esperada da aplicação.

#### Exemplo de fluxo de uso

1. gerar o pacote OTA simples:

   ```powershell
   python asr_loader.py ota_pack app.bin app_ota.bin
   ```

2. opcionalmente validar localmente:

   ```powershell
   python asr_loader.py ota_pack_verify app_ota.bin
   ```

3. opcionalmente inspecionar a `vector table` e a estrutura básica da app:

   ```powershell
   python asr_loader.py ota_pack_inspect app_ota.bin
   ```

4. gravar `app_ota.bin` na flash externa a partir de `0x00000000`;
5. resetar o equipamento para o bootloader do firmware processar a imagem.

---

### ota_pack_verify

Verifica um pacote OTA simples com header de 16 bytes e firmware bruto.
Valida `magic`, `size`, `crc32`, `reserved` e o tamanho total do arquivo.

**Formato:**

```text
ota_pack_verify <arquivo_ota.bin>
```

**Exemplo:**

```powershell
python asr_loader.py ota_pack_verify app_ota.bin
```

---

### ota_pack_inspect

Inspeciona um pacote OTA simples e mostra no LOG a estrutura inicial da aplicação antes da gravação.

Saída esperada:

- header OTA;
- `CRC32` validado;
- primeiros 64 bytes da `vector table`;
- análise estrutural de `MSP`, `Reset_Handler`, `NMI` e `HardFault`.

**Formato:**

```text
ota_pack_inspect <arquivo_ota.bin>
```

**Exemplo:**

```powershell
python asr_loader.py ota_pack_inspect app_ota.bin
```

---

### ota_cript

Gera um pacote OTA criptografado e autenticado, totalmente integrado ao `asr_loader.py` principal.
Use esse arquivo para gravação na flash externa a partir do endereço `0x00000000`.

**Formato:**

```text
ota_cript <arquivo_firmware.bin> [arquivo_saida.bin] [--firmware-version <versao>] [--key-header <boot_security_config.h>]
```

**Exemplo:**

```powershell
python asr_loader.py ota_cript app.bin app_ota_cript.bin --firmware-version 7 --key-header C:\projeto\boot_security_config.h
```

Se `arquivo_saida.bin` não for informado, o nome padrão será `<arquivo_firmware>_ota_cript.bin`.
Se `--key-header` não for informado, a ferramenta tenta localizar o `boot_security_config.h` no caminho padrão; caso ele
não exista no ambiente atual, informe o caminho explicitamente.

#### Formato do pacote

```text
+-------------------------------+
| Header OTA (16 bytes)         |
+-------------------------------+
| Firmware criptografado (N)    |
+-------------------------------+
| Trailer v2 (44 bytes)         |
+-------------------------------+
```

#### Header OTA (16 bytes)

Todos os campos em `little-endian`:

```text
Offset  Tamanho  Campo
0x00    4        magic      = 0xB00710AD
0x04    4        size       = tamanho do firmware em bytes
0x08    4        crc32      = CRC32 IEEE do firmware em claro
0x0C    4        reserved   = 0x00000000
```

#### Trailer v2 (44 bytes)

Todos os campos em `little-endian`:

```text
Offset relativo ao trailer  Tamanho  Campo
0x00                        4        trailer_magic   = 0x41545548
0x04                        4        trailer_version = 2
0x08                        4        flags           = 0x00000003
0x0C                        4        firmware_version
0x10                        8        nonce
0x18                        16       auth_tag
0x28                        4        trailer_crc32
```

#### Como a criptografia funciona

O payload usa um fluxo derivado de `SipHash-64`:

```text
keystream_bloco = SipHash64(nonce || contador, chave, domain=2)
ciphertext      = plaintext XOR keystream
plaintext       = ciphertext XOR keystream
```

O `header` OTA permanece em claro, o payload do firmware vai criptografado e o trailer permanece em claro para permitir
autenticação antes da instalação.

#### O que a autenticação cobre

A `auth_tag` cobre:

```text
[ trailer_version,
  flags,
  firmware_version,
  firmware_size,
  firmware_crc32,
  nonce ] || firmware_criptografado
```

Assim:

- se o payload criptografado for alterado, a autenticação falha antes de apagar a flash interna;
- durante a instalação, o bootloader decripta em streaming e valida o `CRC32` do firmware em claro.

#### O que o firmware/bootloader precisa implementar

Para que o `ota_cript` funcione no bootloader do firmware, o bootloader precisa validar primeiro o pacote criptografado
ainda na flash externa e só então decriptar/copiar a imagem para a flash interna.

Uma estrutura mínima equivalente em C pode seguir esta linha:

```c
typedef struct {
    uint32_t magic;
    uint32_t size;
    uint32_t crc32;
    uint32_t reserved;
} ota_header_t;

typedef struct {
    uint32_t trailer_magic;
    uint32_t trailer_version;
    uint32_t flags;
    uint32_t firmware_version;
    uint8_t  nonce[8];
    uint8_t  auth_tag[16];
    uint32_t trailer_crc32;
} ota_auth_trailer_v2_t;
```

O bootloader e o empacotador devem usar a mesma chave de 16 bytes, definida no macro `BOOT_SECURITY_KEY_BYTES` do
arquivo `boot_security_config.h`.
Se a chave for diferente, a autenticação falha mesmo que o arquivo esteja estruturalmente correto.

#### Sequência de validação recomendada no bootloader

Ao encontrar um pacote OTA seguro na flash externa, o bootloader deve:

1. ler e validar o `header` OTA;
2. localizar o trailer em `offset = 16 + size`;
3. validar `trailer_magic == 0x41545548`;
4. validar `trailer_version == 2`;
5. validar `flags == 0x00000003`;
6. validar o `CRC32` do trailer sem o último campo `trailer_crc32`;
7. montar o prefixo autenticado usando também o `nonce`;
8. recalcular a `auth_tag` usando o firmware criptografado;
9. somente se a autenticação passar, decriptar o firmware em streaming;
10. validar o `CRC32` do firmware em claro contra o campo `crc32` do header;
11. somente então aceitar a imagem para upgrade.

#### Fluxo prático sugerido no firmware

Fluxo típico no bootloader:

1. localizar o pacote OTA na flash externa em `0x00000000`;
2. validar `header` e `trailer` ainda sem decriptar a imagem;
3. recalcular a `auth_tag` sobre o payload criptografado;
4. se a autenticação falhar, abortar o update e manter a aplicação atual;
5. se a autenticação passar, decriptar em blocos e gravar/copiar para a flash interna;
6. calcular o `CRC32` do firmware em claro durante a cópia;
7. comparar o `CRC32` final com o valor do `header`;
8. somente então marcar a atualização como válida.

#### Observações importantes

- o campo `size` do `header` continua representando o tamanho do firmware em claro;
- o `CRC32` do `header` é do firmware em claro, não do payload criptografado;
- a `auth_tag` protege o trailer lógico e o payload criptografado;
- o `nonce` precisa ser lido do trailer e reutilizado na decriptação via`SipHash64(nonce || contador, chave, domain=2)`.

#### Exemplo de fluxo de uso

1. gerar o pacote criptografado e autenticado:

   ```powershell
   python asr_loader.py ota_cript app.bin app_ota_cript.bin --firmware-version 7 --key-header C:\projeto\boot_security_config.h
   ```

2. opcionalmente validar localmente:

   ```powershell
   python asr_loader.py ota_cript_verify app_ota_cript.bin --key-header C:\projeto\boot_security_config.h
   ```

3. gravar `app_ota_cript.bin` na flash externa a partir de `0x00000000`;
4. resetar o equipamento para o bootloader do firmware processar a imagem.

---

### ota_cript_verify

Verifica um pacote OTA criptografado e autenticado com trailer v2 usando a chave configurada.

**Formato:**

```text
ota_cript_verify <arquivo_ota.bin> [--key-header <boot_security_config.h>]
```

**Exemplo:**

```powershell
python asr_loader.py ota_cript_verify app_ota_cript.bin --key-header C:\projeto\boot_security_config.h
```

---

### jump

Executa um jump para um endereço específico.
Faz o microcontrolador executar um salto (jump) para o endereço especificado, transferindo a execução do código para
esse local na memória.
Isso é usado, por exemplo, para iniciar a execução de um novo firmware já gravado na flash.

**Formato:**

```text
jump <endereço_de_jump>
```

**Exemplo:**

```powershell
python asr_loader.py jump 0x08000123
```

Faz um jump para o endereço 0x08000123.
Este comando não retorna nada.

---

### versao_bootloader

Lê a versão do bootloader.
A versão do bootloader é alterada atualizando (regravando) o firmware do bootloader na memória do microcontrolador em
uma área específica reservada para ele.

**Formato:**

```text
versao_bootloader
```

**Exemplo:**

```powershell
python asr_loader.py versao_bootloader
```

Retorna o `version number` bruto do comando `VERSION`.
Exemplo de formato da saída:

```text
VERSION retornado pelo bootloader (valor bruto): 0x00000000 (0)
Bytes retornados (little-endian): 00 00 00 00
```

Os valores acima são apenas ilustrativos; o conteúdo real depende do que o bootloader interno responder no dispositivo.

---

### diagnosticar_otp

Lê a OTP do chip na porta informada e lista as faixas alinhadas de pelo menos
96 bytes que retornaram `FF`. Exibe o serial e os endereços candidatos, sem
mostrar os bytes da OTP. Uma faixa candidata ainda requer reserva pela fabricação.

```powershell
.\asr_loader.exe -p COM3 diagnosticar_otp
```

### diagnosticar_flash_asr

Compara por leitura posições abaixo e acima do limite de 128 KiB de flash.
O resultado registra o comportamento observado e pode ser inconclusivo para
distinguir CB de SE.

```powershell
.\asr_loader.exe -p COM3 diagnosticar_flash_asr
```

Para uma unidade de bancada destinada à regravação, a opção
`--testar-escrita SERIAL_HEX` permite verificar uma escrita independente
acima de 128 KiB. O gravador confere o serial e exige que as páginas de teste
estejam apagadas antes de escrever. Após confirmação, apaga a página de teste
e verifica a restauração. Se a comunicação falhar após a escrita, o padrão
pode permanecer na flash.

```powershell
$serialAsr = Read-Host 'Digite os 16 dígitos hexadecimais do serial da unidade de teste'
.\asr_loader.exe -p COM3 diagnosticar_flash_asr --testar-escrita $serialAsr
```

### ler_otp

Lê dados da área OTP da flash.

**Formato:**

```text
ler_otp <endereço_inicial> <tamanho_em_bytes>
```

**Exemplo:**

```powershell
python asr_loader.py ler_otp 0x1FFF7000 16
```

Lê 16 bytes a partir do endereço 0x1FFF7000.

---

### escrever_otp

Escreve dados na área OTP da flash.
OTP (One-Time Programmable) é uma área especial da memória flash do microcontrolador que pode ser gravada apenas uma
vez.
Após a escrita, os dados não podem ser alterados ou apagados, garantindo que informações críticas (como configurações,
chaves ou identificadores) fiquem permanentemente armazenadas.
A faixa reservada para OTP é de 0x10001C00 a 0x10001FFF.

**Formato:**

```text
escrever_otp <endereço_inicial> <dados_em_hex>
```

**Exemplo:**

```powershell
python asr_loader.py escrever_otp 0x1FFF7000 aabbccdd
```

Escreve os bytes `aabbccdd` no endereço 0x1FFF7000.

---

### ler_opt0

Lê os dados da área OPT0 da flash.

**Formato:**

```text
ler_opt0
```

**Exemplo:**

```powershell
python asr_loader.py ler_opt0
```

Lê os dados da área OPT0.
Exemplo de saída: `1122334455667788`

---

### escrever_opt0

Escreve dados na área OPT0 da flash.
A área OPT0 (Option Bytes 0) é uma seção especial da memória flash do microcontrolador usada para armazenar
configurações de sistema e opções de operação.
Essas opções podem incluir configurações de proteção de memória, modos de boot, e outras funcionalidades que afetam o
comportamento do microcontrolador.

**Formato:**

```text
escrever_opt0 <dados_msb> <dados_lsb>
```

**Exemplo:**

```powershell
python asr_loader.py escrever_opt0 11223344 55667788
```

Escreve os bytes `1122334455667788` na área OPT0.

---

### ler_opt1

Lê os dados da área OPT1 da flash.

**Formato:**

```text
ler_opt1
```

**Exemplo:**

```powershell
python asr_loader.py ler_opt1
```

Lê os dados da área OPT1.
Exemplo de saída: `aabbccddeeff0011`

---

### escrever_opt1

Escreve dados na área OPT1 da flash.
A área OPT1 (Option Bytes 1) é uma seção especial da memória flash do microcontrolador usada para armazenar
configurações adicionais de sistema e opções de operação.
Essas opções podem incluir configurações de proteção de memória, modos de boot, e outras funcionalidades que afetam o
comportamento do microcontrolador.

**Formato:**

```text
escrever_opt1 <dados_msb> <dados_lsb>
```

**Exemplo:**

```powershell
python asr_loader.py escrever_opt1 aabbccdd eeff0011
```

Escreve os bytes `aabbccddeeff0011` na área OPT1.

---

### ler_reg

Lê o valor de um registrador do microcontrolador no endereço especificado.
Ele retorna o valor atual armazenado nesse registrador, permitindo verificar configurações ou estados internos do
hardware.

**Formato:**

```text
ler_reg <endereço_do_registrador>
```

**Exemplo:**

```powershell
python asr_loader.py ler_reg 0x40021000
```

Lê o valor do registrador no endereço 0x40021000.
Exemplo de saída: `0x00000001`

---

### escrever_reg

Escreve um valor em um registrador do microcontrolador, no endereço especificado.
Ele altera diretamente o conteúdo desse registrador, permitindo modificar configurações ou estados do hardware.

**Formato:**

```text
escrever_reg <endereço_do_registrador> <valor_em_hex>
```

**Exemplo:**

```powershell
python asr_loader.py escrever_reg 0x40021000 0x01
```

Escreve o valor `0x01` no registrador no endereço 0x40021000.

---

### ler_mem

Lê uma região maior de memória do ASR in-circuit usando leituras sequenciais de 32 bits.
Esse comando é indicado para consultar áreas maiores de SRAM, flash mapeada ou regiões de periféricos quando você já
conhece os endereços pelo manual de referência.

**Formato:**

```text
ler_mem <endereço_inicial> <tamanho_em_bytes> [arquivo_saida.bin]
```

**Exemplo:**

```powershell
python asr_loader.py ler_mem 0x20000000 256 dump_sram.bin
```

O comando:

- faz leituras sucessivas de 32 bits a partir do endereço informado;
- aceita endereço inicial desalinhado;
- imprime um hexdump formatado no terminal;
- opcionalmente salva o dump bruto em arquivo.

**Observações importantes:**

- a leitura usa o mesmo mecanismo interno de `ler_reg`, repetindo acessos de 32 bits;
- alguns endereços podem não ser legíveis pelo bootloader e podem retornar erro;

### identificar_mcu

Identifica se o dispositivo conectado e um `ASR6601CB` (128 KiB) ou um
`ASR6601SE` (256 KiB), usando exatamente o teste de mapeamento ja validado
no comando `flash`. Esse teste apaga a EEPROM emulada; nao o execute se os
dados dela precisarem ser preservados.

```powershell
python asr_loader.py -p COM9 identificar_mcu
```

### mapa_flash

Lê todos os bytes da flash interna do MCU detectado, imprime o hexdump e gera
automaticamente `mapas_memoria\mapa_flash.bin`. Um nome de arquivo opcional substitui o padrão.

```powershell
python asr_loader.py -p COM9 mapa_flash
```

### mapa_sram

Lê todos os bytes da SRAM do MCU detectado e gera `mapas_memoria\mapa_sram.bin`.

```powershell
python asr_loader.py -p COM9 mapa_sram
```

### mapa_eeprom

Lê todos os 4 KiB da EEPROM emulada do MCU detectado e gera `mapas_memoria\mapa_eeprom.bin`.

```powershell
python asr_loader.py -p COM9 mapa_eeprom
```

Para ASR6601SE, use `--eeprom-ab --mcu se`. O dump bruto contém
as duas páginas físicas, com 8192 bytes no intervalo `0x0803E000–0x0803FFFF`.
A leitura preserva a EEPROM. Use as mesmas opções em `mapa_memoria` para
exibir a faixa.

```powershell
python asr_loader.py -p COM9 mapa_eeprom --eeprom-ab --mcu se
```

Para exportar uma página bruta do PR439v3, use `mapa_eeprom --eeprom-ativa --mcu se`.
O gravador lê as duas páginas e salva 4096 bytes da página com maior geração
indicada nos cabeçalhos reconhecidos. Na ausência de geração, escolhe a página
com dados ou, em caso de empate, a última página física. O console mostra o
endereço e o critério de seleção. As páginas são exportadas como estão na flash,
e a leitura dispensa chave. Se o destino estiver bloqueado, o dump anterior
é preservado e o novo é salvo com um sufixo exclusivo na mesma pasta.
O caminho efetivamente usado aparece em `Dump salvo em`.

Para exportar a página de backup, use `make mapa_eeprom backup` no PR439v3,
ou chame o gravador diretamente:

```powershell
python asr_loader.py -p COM9 mapa_eeprom --eeprom-backup --mcu se
```

O comando usa o mesmo critério para escolher a página ativa e exporta a outra
página para `mapas_memoria/mapa_eeprom_backup.bin`. O dump tem 4 KiB,
mesmo quando a página está apagada. O gravador mostra o endereço escolhido
e a geração indicada pelo cabeçalho, quando disponível.

### Firmware v8: --v8

Usa o mapeamento do firmware v8: somente o ultimo KiB da area de EEPROM
reservada. Assim, a EEPROM passa a ser `0x0801FC00–0x0801FFFF` no CB e
`0x0803FC00–0x0803FFFF` no SE. A opcao afeta apagamento, identificacao e os
comandos de mapa.

```powershell
python asr_loader.py --v8 -p COM9 mapa_eeprom --mcu cb
```

### mapa_memoria

Mostra, de uma vez, as faixas de flash interna, SRAM e EEPROM emulada.

```powershell
python asr_loader.py -p COM9 mapa_memoria
```

Sem `--mcu`, os comandos usam a mesma identificacao validada pelo `flash`; por
isso apagam a EEPROM emulada durante a identificacao. Para preservar a EEPROM,
informe o modelo conhecido: `mapa_eeprom eeprom.bin --mcu cb`.

- para regiões muito grandes, prefira informar um arquivo de saída e analisar o dump depois.

---

### snapshot

Lê registradores definidos em um perfil de snapshot, permitindo coletas repetíveis de estado do firmware.

**Formato:**

```text
snapshot [--profile <perfil-ou-arquivo.json>] [--output <snapshot.json>] [--json]
```

**Exemplo:**

```powershell
python asr_loader.py -p COM3 snapshot
python asr_loader.py -p COM3 snapshot --json --output snapshot.json
```

Perfis builtin:

- `asr6601`: primeiras palavras da vector table da aplicação (`MSP`, `Reset_Handler`, `NMI`, `HardFault`);
- `vector`: quatro primeiras palavras da vector table.

Também é possível passar um arquivo JSON de perfil:

```json
{
  "description": "registradores customizados",
  "registers": [
    {
      "name": "app_msp",
      "address": "0x08000000"
    },
    {
      "name": "app_reset",
      "address": "0x08000004"
    }
  ]
}
```

---

### help

Mostra a ajuda com todos os comandos e opções.

**Formato:**

```text
help
```

**Exemplo:**

```powershell
python asr_loader.py help
```

Mostra a ajuda com todos os comandos e opções.

---

### versao

Mostra a versão do ASR Loader. **Formato:**

```text
versao
```

**Exemplo:**

```powershell
python asr_loader.py versao
```

Mostra a versão do ASR Loader, preenchida automaticamente a partir do `README.md`.
Exemplo de saída: `ASR_Loader: v1.0 (2024-06-01)`
---

## Observações

- Para listar as portas seriais disponíveis, basta executar sem o parâmetro `--port`.
- Use o parâmetro `--verbose` ou `-v` para obter mais detalhes da comunicação.
- Comandos concluídos com sucesso retornam código de saída `0`; falhas retornam código `1`.
- Para depurar problemas de conexão, rode primeiro `comdiag`, depois `doctor --testeboot` e `testeboot --sweep` com
  `--log-file`/`--trace-json`.

---

## Exemplo de flash.bat

```bat
.\asr_loader.exe ^
-v ^
flash 0x08000000 .\abnt-620-debug-1.bin
pause
```
