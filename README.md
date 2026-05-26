# ASR Loader HD
`ASR_Loader_HD: v{{BUILD_VERSION}}`
`{{BUILD_DATE}}`

Ferramenta para gravação e debug de microcontroladores ASR via porta serial.

---

## Sumário
- [Tremo Loader HD](#tremo-loader-hd)
  - [Ambiente de desenvolvimento](#ambiente-de-desenvolvimento)
  - [Criar o novo .exe](#criar-o-novo-exe)
  - [Substituir o tremo_loader.exe em projetos com ASR:](#substituir-o-tremo_loaderexe-em-projetos-com-asr)
- [Uso](#uso)
- [Parâmetros globais](#parâmetros-globais)
  - [COM PORT: -p ou --port](#com-port--p-ou---port)
  - [Baudrate: -b ou --baudrate](#baudrate--b-ou---baudrate)
  - [Modo log verboso: -v ou --verbose](#modo-log-verboso--v-ou---verbose)
  - [Timeout de conexão: -t ou --timeout](#timeout-de-conexão--t-ou---timeout)
  - [Manter EEPROM: -e ou --eeprom](#manter-eeprom--e-ou---eeprom)
  - [Help: -h ou --help](#help--h-ou---help)
- [Comandos](#comandos)
  - [make](#make)
  - [erase](#erase)
  - [flash](#flash)
  - [verify](#verify)
  - [reset](#reset)
  - [clear_eeprom](#clear_eeprom)
  - [serial](#serial)
  - [ota_pack](#ota_pack)
  - [ota_pack_verify](#ota_pack_verify)
  - [ota_assinado](#ota_assinado)
  - [ota_assinado_verify](#ota_assinado_verify)
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
  - [help](#help)
  - [versao](#versao)
- [Observações](#observações)
- [Exemplo de flash.bat](#exemplo-de-flashbat)

---

## Tremo Loader HD
O Tremo Loader HD é uma ferramenta de linha de comando para gravação e debug de microcontroladores ASR via porta serial.
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
---

### Criar o novo .exe
```bat
build.bat
```
ou
```powershell
pyinstaller --onefile tremo_loader.py
```
ou
```powershell
py -m PyInstaller --onefile tremo_loader.py
```
---

### Substituir o tremo_loader.exe em projetos com ASR:
Este script realiza um build e copia automaticamente o executável versionado mais recente de `dist\tremo_loader-v*.exe` para as pastas de tools dos projetos com ASR.
Também gera um arquivo `MANUAL_tremo_loader.md` com a versão e a data do último executável encontrado em `dist`, preenchidas automaticamente a partir do `README.md`.
```bat
atualizar-builds.bat
```
---

## Uso

Execute o script via terminal:
```powershell
py tremo_loader.py <comando> [opções] [argumentos]
```
ou
```powershell
.\tremo_loader.exe <comando> [opções] [argumentos]
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

### Baudrate: -b ou --baudrate
Configura o baudrate.
Por padrão vem com 921600, caso não seja passado nada.

**Formato:**
```text
-b <baudrate>
--baudrate <baudrate>
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
python tremo_loader.py flash 0x08000000 app.bin
```
O `make` é apenas um atalho e não tem funcionalidades adicionais além de simplificar a execução dos comandos do `tremo_loader.py` com os parâmetros globais.
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
python tremo_loader.py erase 0x08000000 4096
```
Apaga 4096 bytes a partir do endereço 0x08000000.

---

### flash
Apaga e grava arquivos na flash.

**Formato:**
```text
flash <endereço_inicial> <arquivo.bin>
```

**Exemplo:**
```powershell
python tremo_loader.py flash 0x08000000 app.bin
```
Grava o arquivo `app.bin` no endereço 0x08000000.

---

### verify
Verifica o conteúdo da flash comparando com um arquivo.

**Formato:**
```text
verify <endereço_inicial> <arquivo.bin>
```

**Exemplo:**
```powershell
python tremo_loader.py verify 0x08000000 app.bin
```
Verifica se o conteúdo da flash a partir de 0x08000000 é igual ao arquivo `app.bin`.
Retorna "Verificacao completa! Flash igual ao arquivo." se for igual,
ou "ERROR: flash diferente do arquivo" se houver diferença.

---

### reset
Reinicia o dispositivo.

**Formato:**
```text
reset
```

**Exemplo:**
```powershell
python tremo_loader.py reset
```
Reinicia o dispositivo conectado.

---

### clear_eeprom
Apaga toda a memória EEPROM do microcontrolador.

**Formato:**
```text
clear_eeprom
```

**Exemplo:**
```powershell
python tremo_loader.py clear_eeprom
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
python tremo_loader.py serial
```
Retorna o número de serial do dispositivo com 16 bytes.
Exemplo de saída: `0123456789abcdef`

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
python tremo_loader.py ota_pack app.bin app_ota.bin
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

#### Exemplo de fluxo de uso

1. gerar o pacote OTA simples:

   ```powershell
   python tremo_loader.py ota_pack app.bin app_ota.bin
   ```

2. opcionalmente validar localmente:

   ```powershell
   python tremo_loader.py ota_pack_verify app_ota.bin
   ```

3. gravar `app_ota.bin` na flash externa a partir de `0x00000000`;
4. resetar o equipamento para o bootloader do firmware processar a imagem.

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
python tremo_loader.py ota_pack_verify app_ota.bin
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
python tremo_loader.py ota_assinado app.bin app_assinado.bin --firmware-version 7 --key-header C:\projeto\boot_security_config.h
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

#### Exemplo de fluxo de uso

1. gerar o pacote assinado:
   ```powershell
   python tremo_loader.py ota_assinado app.bin app_ota_assinado.bin --firmware-version 7 --key-header C:\projeto\boot_security_config.h
   ```

2. opcionalmente validar localmente:
   ```powershell
   python tremo_loader.py ota_assinado_verify app_ota_assinado.bin --key-header C:\projeto\boot_security_config.h
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
python tremo_loader.py ota_assinado_verify app_ota_assinado.bin --key-header C:\projeto\boot_security_config.h
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
python tremo_loader.py jump 0x08000123
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
python tremo_loader.py versao_bootloader
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
python tremo_loader.py ler_otp 0x1FFF7000 16
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
python tremo_loader.py escrever_otp 0x1FFF7000 aabbccdd
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
python tremo_loader.py ler_opt0
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
python tremo_loader.py escrever_opt0 11223344 55667788
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
python tremo_loader.py ler_opt1
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
python tremo_loader.py escrever_opt1 aabbccdd eeff0011
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
python tremo_loader.py ler_reg 0x40021000
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
python tremo_loader.py escrever_reg 0x40021000 0x01
```
Escreve o valor `0x01` no registrador no endereço 0x40021000.

---

### help
Mostra a ajuda com todos os comandos e opções.

**Formato:**
```text
help
```

**Exemplo:**
```powershell
python tremo_loader.py help
```
Mostra a ajuda com todos os comandos e opções.

---

### versao
Mostra a versão do Tremo Loader HD.
**Formato:**
```text
versao
```
**Exemplo:**
```powershell
python tremo_loader.py versao
```
Mostra a versão do Tremo Loader HD, preenchida automaticamente a partir do `README.md`.
Exemplo de saída: `ASR_Loader_HD: v1.0 (2024-06-01)`
---

## Observações

- Para listar as portas seriais disponíveis, basta executar sem o parâmetro `--port`.
- Use o parâmetro `--verbose` ou `-v` para obter mais detalhes da comunicação.

---

## Exemplo de flash.bat
```bat
.\tremo_loader.exe ^
-v ^
flash 0x08000000 .\abnt-620-debug-1.bin
pause
```
