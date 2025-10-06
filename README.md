# tremo_loader.py

Ferramenta para gravação e debug de microcontroladores ASR via porta serial.

---

## Instalação

Requisitos:
- Python 3.x
- Instalar dependências:
```
pip install -r requirements.txt
```

---

## Uso

Execute o script via terminal:
```
py tremo_loader.py <comando> [opções] [argumentos]
```
ou
```
.\tremo_loader.exe <comando> [opções] [argumentos]
```
ou
```
make <comando> [opções] [argumentos]
```

---

## Criar o novo .exe
```
pyinstaller --onefile tremo_loader.py
```
ou
```
py -m PyInstaller --onefile tremo_loader.py
```

---

## Parâmetros globais
### -p ou --port
Configura a porta serial

**Exemplo:**
```
make -p COM3 flash 0x08000000 app.bin
```
---

### -b ou --baudrate
Configura o paudrate
Por padrão vem com 921600, caso não seja passado nada

**Exemplo:**
```
make -b 115200 flash 0x08000000 app.bin
```
---

### -v ou --verbose
Configura modo verboso. Mostra todos os dados trafegados pela serial.

**Exemplo:**
```
make -v flash 0x08000000 app.bin
```
---

### -t ou --timeout
Configura o timeout em segundos. Padrão é 2 segundos.
**Exemplo:**
```
make -t 10 flash 0x08000000 app.bin
```
---

### -h ou --help
Mostra a ajuda com todos os comandos e opções.

**Exemplo:**
```
make -h
```
---

## Comandos

### erase
Apaga uma área da flash a partir de um endereço específico.

**Formato:**
```
erase <endereço_inicial> <tamanho_em_bytes>
```

**Exemplo:**
```
python tremo_loader.py erase 0x08000000 4096
```
Apaga 4096 bytes a partir do endereço 0x08000000.

---

### flash
Apaga e grava arquivos na flash.

**Formato:**
```
flash <endereço_inicial> <arquivo.bin>
```

**Exemplo:**
```
python tremo_loader.py flash 0x08000000 app.bin
```
Grava o arquivo `app.bin` no endereço 0x08000000.

---

### escrever_otp
Escreve dados na área OTP da flash.
OTP (One-Time Programmable) é uma área especial da memória flash do microcontrolador que pode ser gravada apenas uma vez.
Após a escrita, os dados não podem ser alterados ou apagados, garantindo que informações críticas (como configurações, chaves ou identificadores) fiquem permanentemente armazenadas.

**Formato:**
```
escrever_otp <endereço_inicial> <dados_em_hex>
```

**Exemplo:**
```
python tremo_loader.py escrever_otp 0x1FFF7000 aabbccdd
```
Escreve os bytes `aabbccdd` no endereço 0x1FFF7000.

---

### ler_otp
Lê dados da área OTP da flash.

**Formato:**
```
ler_otp <endereço_inicial> <tamanho_em_bytes>
```

**Exemplo:**
```
python tremo_loader.py ler_otp 0x1FFF7000 16
```
Lê 16 bytes a partir do endereço 0x1FFF7000.

---

### serial
Lê o número de série do microcontrolador.
O número de série é um identificador único atribuído a cada microcontrolador durante o processo de fabricação.
Ele é usado para identificar individualmente cada dispositivo, permitindo rastreamento, autenticação e controle de qualidade.

**Formato:**
```
serial
```

**Exemplo:**
```
python tremo_loader.py serial
```
Retorna o número de serial do dispositivo com 16 bytes.
Exemplo de saída: `0123456789abcdef`

---

### reset
Reinicia o dispositivo.

**Formato:**
```
reset
```

**Exemplo:**
```
python tremo_loader.py reset
```
Reinicia o dispositivo conectado.

---

### verify
Verifica o conteúdo da flash comparando com um arquivo.

**Formato:**
```
verify <endereço_inicial> <arquivo.bin>
```

**Exemplo:**
```
python tremo_loader.py verify 0x08000000 app.bin
```
Verifica se o conteúdo da flash a partir de 0x08000000 é igual ao arquivo `app.bin`.
Retorna "Verificacao completa! Fash igual ao arquivo." se for igual,
ou "ERROR: flash diferente do arquivo" se houver diferença.

---

### versao_bootloader
Lê a versão do bootloader.
A versão do bootloader é alterada atualizando (regravando) o firmware do bootloader na memória do microcontrolador em uma área específica reservada para ele.

**Formato:**
```
versao_bootloader
```

**Exemplo:**
```
python tremo_loader.py versao_bootloader
```
Retorna a versão do bootloader.
Exemplo de saída: `1.0.0`

---

### ler_reg
Lê o valor de um registrador do microcontrolador no endereço especificado.
Ele retorna o valor atual armazenado nesse registrador, permitindo verificar configurações ou estados internos do hardware.

**Formato:**
```
ler_reg <endereço_do_registrador>
```

**Exemplo:**
```
python tremo_loader.py ler_reg 0x40021000
```
Lê o valor do registrador no endereço 0x40021000.
Exemplo de saída: `0x00000001`

---

### escrever_reg
Escreve um valor em um registrador do microcontrolador, no endereço especificado.
Ele altera diretamente o conteúdo desse registrador, permitindo modificar configurações ou estados do hardware.

**Formato:**
```
escrever_reg <endereço_do_registrador> <valor_em_hex>
```

**Exemplo:**
```
python tremo_loader.py escrever_reg 0x40021000 0x01
```
Escreve o valor `0x01` no registrador no endereço 0x40021000.

---

### jump
Executa um jump para um endereço específico.
Faz o microcontrolador executar um salto (jump) para o endereço especificado, transferindo a execução do código para esse local na memória.
Isso é usado, por exemplo, para iniciar a execução de um novo firmware já gravado na flash.

**Formato:**
```
jump <endereço_de_jump>
```

**Exemplo:**
```
python tremo_loader.py jump 0x08000123
```
Faz um jump para o endereço 0x08000123.
Este comando não retorna nada.

---

## Observações

- Para listar as portas seriais disponíveis, basta executar sem o parâmetro `--port`.
- Use o parâmetro `--verbose` ou `-v` para obter mais detalhes da comunicação.

## Exemplo de flash.bat
```
.\tremo_loader.exe ^
-v ^
flash 0x08000000 .\abnt-620-debug-1.bin
pause
```
