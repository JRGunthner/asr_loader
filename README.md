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
  - [Help: -h ou --help](#help--h-ou---help)
- [Comandos](#comandos)
  - [make](#make)
  - [erase](#erase)
  - [flash](#flash)
  - [preflight](#preflight)
  - [firmware_inspect](#firmware_inspect)
  - [verify](#verify)
  - [reset](#reset)
  - [hw_reset](#hw_reset)
  - [dtr1 / dtr0 / rts1 / rts0](#dtr1--dtr0--rts1--rts0)
  - [clear_eeprom](#clear_eeprom)
  - [serial](#serial)
  - [diag](#diag)
  - [doctor](#doctor)
  - [probe](#probe)
  - [ota_pack](#ota_pack)
  - [ota_pack_verify](#ota_pack_verify)
  - [ota_pack_inspect](#ota_pack_inspect)
  - [ota_assinado](#ota_assinado)
  - [ota_assinado_verify](#ota_assinado_verify)
  - [ota_cript](#ota_cript)
  - [ota_cript_verify](#ota_cript_verify)
  - [jump](#jump)
  - [versao_bootloader](#versao_bootloader)
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
Ele suporta uma variedade de comandos para interagir com o bootloader dos microcontroladores ASR, permitindo operações como gravação de firmware, leitura/escrita de memória, controle de boot e geração de pacotes OTA.
A ferramenta é projetada para ser fácil de usar, com uma interface de linha de comando intuitiva e opções de configuração flexíveis.
Ela é especialmente útil para desenvolvedores que trabalham com microcontroladores ASR, oferecendo uma solução eficiente para gerenciamento de firmware e depuração.

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
Este script realiza um build e copia automaticamente o executável versionado mais recente de `dist\_loader-v*.exe` para as pastas de tools dos projetos com ASR.
Também gera um arquivo `MANUAL_asr_loader.md` com a versão e a data do último executável encontrado em `dist`, preenchidas automaticamente a partir do `README.md`.
```bat
atualizar-builds.bat
```
---

## Uso

Execute o script via terminal:
```powershell
py asr_loader.py <comando> [opções] [argumentos]
```
ou
```powershell
.\asr_loader.exe <comando> [opções] [argumentos]
```
ou
```powershell
make <comando> [opções] [argumentos]
```
---

## Parâmetros globais
### COM PORT: -p ou --port
Configura a porta serial.
Caso não seja passado nada, lista as portas seriais disponíveis e tenta conectar na primeira que encontrar o dispositivo.

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
Salva em arquivo os principais eventos da execução, incluindo porta usada, parâmetros de conexão, sequência `DTR/RTS`, pacotes `TX/RX` e erros.

**Formato:**
```text
--log-file <arquivo.log>
```

**Exemplo:**
```powershell
python asr_loader.py -p COM3 --log-file debug_gravacao.log probe
```

Esse log é indicado para depurar bancada, timing de auto boot e falhas intermitentes de comunicação.

---

### Salvar trace estruturado: --trace-json
Salva eventos estruturados em JSON Lines (`.jsonl`) para análise automática em scripts.
O trace inclui eventos como `serial_tx` e `serial_result`, com comando, tamanho de pacote, status, duração e erro quando houver.

**Formato:**
```text
--trace-json <arquivo.jsonl>
```

**Exemplo:**
```powershell
python asr_loader.py -p COM3 --trace-json trace_probe.jsonl probe --json
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
Por padrão, antes de conectar no bootloader, o ASR Loader aciona as linhas de controle da serial para colocar o MCU em modo de gravação.

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

Se o seu hardware já coloca o ASR manualmente em modo boot, ou se você estiver depurando a conexão, desative o acionamento automático:

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
O comando `make` é um atalho para executar o script com os parâmetros globais de forma mais simples. Ele é especialmente útil para quem está acostumado a usar o `make` em projetos de firmware e deseja uma sintaxe mais concisa para os comandos de gravação e debug.
**Formato:**
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
O `make` é apenas um atalho e não tem funcionalidades adicionais além de simplificar a execução dos comandos do `asr_loader.py` com os parâmetros globais.
Quando você usa `make`, ele automaticamente passa os parâmetros globais configurados para o comando que você deseja executar, tornando a linha de comando mais limpa e fácil de usar.

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
Antes de conectar no hardware, o comando executa um preflight local do plano de gravação para validar arquivos, tamanhos, CRC32, endereços e overlaps.

**Formato:**
```text
flash <endereço_inicial> <arquivo.bin>
```

**Exemplo:**
```powershell
python asr_loader.py flash 0x08000000 app.bin
```
Grava o arquivo `app.bin` no endereço 0x08000000.

---

### preflight
Valida localmente um plano de gravação sem abrir a porta serial.
É útil para checar argumentos de `flash` em scripts antes de chegar na bancada.

**Formato:**
```text
preflight <endereço_inicial> <arquivo.bin> [<endereço_inicial> <arquivo.bin> ...] [--strict-app-range] [--json]
```

**Exemplo:**
```powershell
python asr_loader.py preflight 0x08000000 app.bin
python asr_loader.py preflight 0x08000000 app.bin --json
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
Com `--boot`, o comando ativa `DTR`, pulsa `RTS` e depois libera `DTR`, usando os tempos configurados por `--boot-reset-delay` e `--boot-release-delay`.

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

Observação: em adaptadores como CP2102 e nos circuitos de reset/boot com transistor, o nível elétrico medido no pino do MCU pode ficar invertido em relação ao estado lógico enviado pelo software. Para validar, meça diretamente no pino `DTR`/`RTS` do CP2102 e depois no ponto do circuito que chega ao MCU.

---

### clear_eeprom
Apaga toda a memória EEPROM do microcontrolador.

**Formato:**
```text
clear_eeprom
```

**Exemplo:**
```powershell
python asr_loader.py clear_eeprom
```
Apaga toda a memória EEPROM do microcontrolador.
Exemplo de saída: `EEPROM apagada com sucesso!`

---

### serial
Lê o número de série do microcontrolador.
O número de série é um identificador único atribuído a cada microcontrolador durante o processo de fabricação.
Ele é usado para identificar individualmente cada dispositivo, permitindo rastreamento, autenticação e controle de qualidade.

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

### diag
Mostra informações úteis para desenvolvimento e depuração sem conectar no bootloader.
Inclui versão do ASR Loader, data/fonte do build, Python em uso, versão do `pyserial` e detalhes das portas seriais detectadas.

**Formato:**
```text
diag [--json]
```

**Exemplo:**
```powershell
python asr_loader.py diag
```

**Exemplo em JSON:**
```powershell
python asr_loader.py diag --json
```

Use esse comando ao abrir um reporte de problema de gravação, porta COM ou driver USB-serial.

---

### doctor
Executa um diagnóstico guiado do ambiente e, opcionalmente, testa sincronismo com o bootloader.

**Formato:**
```text
doctor [--probe] [--json]
```

**Exemplo:**
```powershell
python asr_loader.py -p COM3 doctor
python asr_loader.py -p COM3 doctor --probe --json
```

O relatório inclui:

- versão do ASR Loader, Python e `pyserial`;
- portas seriais detectadas;
- porta selecionada;
- configuração de auto boot;
- resultado opcional do `probe`;
- recomendações objetivas para o próximo teste de bancada.

---

### probe
Testa entrada no bootloader e sincronismo sem apagar, gravar ou alterar memória flash.
É o primeiro comando recomendado para validar o circuito de auto boot e a comunicação serial.

**Formato:**
```text
probe [--json]
probe --sweep [--sweep-bauds <lista>] [--sweep-reset-delays <lista>] [--sweep-release-delays <lista>] [--json]
```

**Exemplo:**
```powershell
python asr_loader.py -p COM3 probe
```

**Exemplo de sweep de timings:**
```powershell
python asr_loader.py -p COM3 probe --sweep --sweep-bauds 115200,921600 --sweep-reset-delays 0.05,0.1,0.2 --sweep-release-delays 0.05,0.1,0.2
```

**Exemplo com log:**
```powershell
python asr_loader.py -p COM3 --log-file probe.log probe
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

Para que o `ota_pack` funcione no bootloader do firmware, o bootloader precisa ler o pacote OTA da flash externa, validar o header e a integridade do firmware, e só então aceitar a imagem.

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
- diferente do `ota_assinado`, o `ota_pack` fornece apenas verificação de integridade, não autenticação criptográfica.

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

### ota_assinado
Gera um pacote OTA assinado com header OTA, trailer de autenticação e validação local do resultado.
Use esse arquivo para gravação na flash externa a partir do endereço `0x00000000`.

**Formato:**
```text
ota_assinado <arquivo_firmware.bin> [arquivo_saida.bin] [--firmware-version <versao>] [--key-header <boot_security_config.h>]
```

**Exemplo:**
```powershell
python asr_loader.py ota_assinado app.bin app_assinado.bin --firmware-version 7 --key-header C:\projeto\boot_security_config.h
```
Se `arquivo_saida.bin` não for informado, o nome padrão será `<arquivo_firmware>_ota_assinado.bin`.
Se `--key-header` não for informado, a ferramenta tenta localizar o `boot_security_config.h` no caminho padrão; caso ele não exista no ambiente atual, informe o caminho explicitamente.

#### O que o firmware/bootloader precisa implementar

Para que o `ota_assinado` funcione no bootloader do firmware, o bootloader precisa saber ler o pacote OTA da flash externa, validar integridade e autenticação, e só então aceitar a imagem.

O formato gerado pela ferramenta é:

```text
+-------------------------------+
| Header OTA (16 bytes)         |
+-------------------------------+
| Firmware bruto (N bytes)      |
+-------------------------------+
| Trailer de autenticacao       |
| (36 bytes)                    |
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

#### Trailer de autenticação (36 bytes)

Também em `little-endian`:

```text
Offset relativo ao trailer  Tamanho  Campo
0x00                        4        trailer_magic   = 0x41545548
0x04                        4        trailer_version = 1
0x08                        4        flags           = 1   (SipHash-128)
0x0C                        4        firmware_version
0x10                        16       auth_tag
0x20                        4        trailer_crc32   = CRC32 dos 32 bytes anteriores do trailer
```

#### Como a `auth_tag` é calculada

O cálculo usado pelo gerador está em `src/ota_assinado.py` e segue esta sequência:

1. calcular o `crc32` do firmware bruto;
2. montar o prefixo autenticado com 5 palavras de 32 bits:

   ```text
   [ trailer_version,
     flags,
     firmware_version,
     firmware_size,
     firmware_crc32 ]
   ```

3. concatenar `prefixo + firmware`;
4. calcular `SipHash-128` com a chave de 16 bytes;
5. gravar o resultado em `auth_tag`.

Em outras palavras:

```text
auth_tag = SipHash128(prefixo_autenticado || firmware, chave_16_bytes)
```

#### Chave usada no bootloader

O `ota_assinado` lê a chave do macro `BOOT_SECURITY_KEY_BYTES` dentro de `boot_security_config.h`.
O bootloader do firmware precisa usar exatamente a mesma chave.
O parser do `asr_loader` aceita tanto a forma em linha única quanto a forma multi-linha com sufixos `U`/`UL` nos bytes.

Exemplo esperado pelo empacotador:

```c
#define BOOT_SECURITY_KEY_BYTES { \
    0x00U, 0x01U, 0x02U, 0x03U, \
    0x04U, 0x05U, 0x06U, 0x07U, \
    0x08U, 0x09U, 0x0AU, 0x0BU, \
    0x0CU, 0x0DU, 0x0EU, 0x0FU  \
}
```

Se a chave do bootloader e a chave usada no empacotamento forem diferentes, a validação vai falhar.

#### Estruturas mínimas no bootloader

Uma implementação equivalente em C pode usar algo nesta linha:

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
    uint8_t  auth_tag[16];
    uint32_t trailer_crc32;
} ota_auth_trailer_t;
```

#### Sequência de validação recomendada no bootloader

Ao encontrar um pacote OTA na flash externa, o bootloader deve:

1. ler e validar o `header`;
2. verificar se `magic == 0xB00710AD`;
3. verificar se `size` é compatível com o espaço disponível;
4. localizar o trailer em `offset = 16 + size`;
5. validar `trailer_magic == 0x41545548`;
6. validar `trailer_version == 1`;
7. validar `flags == 1`;
8. calcular `CRC32` do firmware e comparar com o `crc32` do header;
9. calcular `CRC32` dos primeiros 32 bytes do trailer e comparar com `trailer_crc32`;
10. montar o mesmo prefixo autenticado usado no empacotador;
11. recalcular a `auth_tag` com a chave embutida no bootloader;
12. comparar a `auth_tag` calculada com a `auth_tag` recebida no trailer;
13. somente se tudo passar, aceitar a imagem para upgrade.

#### Fluxo prático sugerido no firmware

Fluxo típico no bootloader:

1. bootloader inicia;
2. detecta pacote OTA na flash externa em `0x00000000`;
3. valida header, firmware e trailer;
4. se a autenticação falhar, aborta o update e mantém o firmware atual;
5. se a autenticação passar, grava/copia o firmware para a flash de execução;
6. opcionalmente grava estado de sucesso e limpa a imagem OTA consumida.

#### Observações importantes

- todos os inteiros usados no pacote estão em `little-endian`;
- o `CRC32` usado aqui é o IEEE (`binascii.crc32` no Python);
- a autenticação é feita sobre o firmware bruto, não sobre a imagem já gravada na flash interna;
- o campo `firmware_version` pode ser usado pelo bootloader para política de anti-rollback, se desejar;
- hoje a ferramenta gera `trailer_version = 1` e `flags = 1`, então o bootloader deve validar exatamente esses valores.
- se você também precisa de confidencialidade do payload na flash externa, use `ota_cript`.

#### Exemplo de fluxo de uso

1. gerar o pacote assinado:
   ```powershell
   python asr_loader.py ota_assinado app.bin app_ota_assinado.bin --firmware-version 7 --key-header C:\projeto\boot_security_config.h
   ```

2. opcionalmente validar localmente:
   ```powershell
   python asr_loader.py ota_assinado_verify app_ota_assinado.bin --key-header C:\projeto\boot_security_config.h
   ```

3. gravar `app_ota_asinado.bin` na flash externa a partir de `0x00000000`;
4. resetar o equipamento para o bootloader do firmware processar a imagem.

---

### ota_assinado_verify
Verifica um pacote OTA assinado usando o trailer de autenticação e a chave configurada.

**Formato:**
```text
ota_assinado_verify <arquivo_ota_assinado.bin> [--key-header <boot_security_config.h>]
```

**Exemplo:**
```powershell
python asr_loader.py ota_assinado_verify app_ota_assinado.bin --key-header C:\projeto\boot_security_config.h
```

---

### ota_cript
Gera um pacote OTA assinado + criptografado, totalmente integrado ao `asr_loader.py` principal.
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
Se `--key-header` não for informado, a ferramenta tenta localizar o `boot_security_config.h` no caminho padrão; caso ele não exista no ambiente atual, informe o caminho explicitamente.

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

O payload usa um fluxo derivado de `SipHash-64` já compatível com o `boot_assinado`:

```text
keystream_bloco = SipHash64(nonce || contador, chave, domain=2)
ciphertext      = plaintext XOR keystream
plaintext       = ciphertext XOR keystream
```

O `header` OTA permanece em claro, o payload do firmware vai criptografado e o trailer permanece em claro para permitir autenticação antes da instalação.

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

Para que o `ota_cript` funcione no bootloader do firmware, o bootloader precisa validar primeiro o pacote criptografado ainda na flash externa e só então decriptar/copiar a imagem para a flash interna.

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

O bootloader deve usar exatamente a mesma chave `BOOT_SECURITY_KEY_BYTES` do empacotador.
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
- o `nonce` precisa ser lido do trailer e reutilizado na decriptação via `SipHash64(nonce || contador, chave, domain=2)`;
- o comando `ota_cript_verify` também aceita pacotes legados do `ota_assinado` (`trailer_version = 1`) para facilitar testes de bancada.

#### Exemplo de fluxo de uso

1. gerar o pacote assinado + criptografado:

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
Verifica um pacote OTA assinado + criptografado com trailer v2 usando a chave configurada.

Este verificador também aceita pacotes legados do `ota_assinado` (`trailer_version = 1`) para facilitar validação local em um único fluxo.

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
Faz o microcontrolador executar um salto (jump) para o endereço especificado, transferindo a execução do código para esse local na memória.
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
A versão do bootloader é alterada atualizando (regravando) o firmware do bootloader na memória do microcontrolador em uma área específica reservada para ele.

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
OTP (One-Time Programmable) é uma área especial da memória flash do microcontrolador que pode ser gravada apenas uma vez.
Após a escrita, os dados não podem ser alterados ou apagados, garantindo que informações críticas (como configurações, chaves ou identificadores) fiquem permanentemente armazenadas.
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
A área OPT0 (Option Bytes 0) é uma seção especial da memória flash do microcontrolador usada para armazenar configurações de sistema e opções de operação.
Essas opções podem incluir configurações de proteção de memória, modos de boot, e outras funcionalidades que afetam o comportamento do microcontrolador.

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
A área OPT1 (Option Bytes 1) é uma seção especial da memória flash do microcontrolador usada para armazenar configurações adicionais de sistema e opções de operação.
Essas opções podem incluir configurações de proteção de memória, modos de boot, e outras funcionalidades que afetam o comportamento do microcontrolador.

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
Ele retorna o valor atual armazenado nesse registrador, permitindo verificar configurações ou estados internos do hardware.

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
Esse comando é indicado para consultar áreas maiores de SRAM, flash mapeada ou regiões de periféricos quando você já conhece os endereços pelo manual de referência.

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
    { "name": "app_msp", "address": "0x08000000" },
    { "name": "app_reset", "address": "0x08000004" }
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
Mostra a versão do ASR Loader.
**Formato:**
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
- Para depurar problemas de conexão, rode primeiro `diag`, depois `doctor --probe` e `probe --sweep` com `--log-file`/`--trace-json`.

---

## Exemplo de flash.bat
```bat
.\asr_loader.exe ^
-v ^
flash 0x08000000 .\abnt-620-debug-1.bin
pause
```
