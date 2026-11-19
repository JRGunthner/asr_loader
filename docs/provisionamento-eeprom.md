# Provisionamento da EEPROM em produção

A estação usa uma única chave da EEPROM de 32 bytes para toda a frota e todas
as versões. O arquivo local contém exatamente 64 dígitos hexadecimais, admitindo
espaços e quebras de linha apenas nas extremidades. Informe o caminho pela
variável de ambiente `ASR_ARQUIVO_CHAVE_EEPROM`, que pode ser definida apenas
na sessão da gravação. Mantenha o arquivo fora de pacotes, do firmware e
do controle de versão. O executável recebe os bytes em memória pelo protocolo
serial do bootloader. Use uma estação com acesso restrito, incluindo acesso ao
barramento serial e aos arquivos de fabricação.

## Produção com rodapé ASRPROD

O fluxo atual aceita um único arquivo de firmware com `flash --producao-bin`.
A opção `--mcu` continua indicando a variante conferida na placa. Para conferir
um arquivo local sem comunicação serial e sem carregar a chave, use
`asr_loader producao_inspect arquivo.bin --mcu ASR6601SE`.

O rodapé ASRPROD v1 tem 70 bytes e declara o quadro OTP de formato 1.
O gravador converte a versão decimal do rodapé para BCD ao provisionar.
O caminho legado com manifesto continua disponível e grava o mesmo quadro.
O contrato do rodapé está em `core/make/producao-binario.md` no firmware.

## Reserva física e aprovação

O *ASR6601 Reference Manual* v1.3.0, §§10.3.1 e 10.3.2, identifica a OTP de
1 KiB em `0x10001C00–0x10001FFF` e a programação simples em unidades de 8
bytes. O driver `asr_flash_otp_program_data` recusa bytes previamente
programados e usa `PROGRAM_DATA0/1` para as unidades de oito bytes. O
*BootLoader Communication Notes* v0.1.0, §§1.4.6, 1.4.7 e 1.4.13, descreve
WROTP, RDOTP e o número de série de oito bytes.

A reserva inicial foi registrada em 2026-11-18. Com o mapa revisado, a faixa **`0x10001C00–0x10001C5F`** foi alocada ao registro
EEPROM v1 do produto PR439v3. O responsável pela fabricação confirmou que os
procedimentos disponíveis estão no repositório. A revisão do gravador e do
firmware encontrou apenas referências genéricas e exemplos dos comandos OTP
nessa faixa. O diagnóstico da unidade `9f0d050a02243201` retornou `FF` em
todo o intervalo reservado. O exemplo legado de escrita em `0x10001C00`
incide sobre a reserva e deve ficar fora do procedimento de bancada.

A referência da reserva é `PR439v3/EEPROM-v1/2026-11-18`. Compile com
`EEPROM_CHAVE_OTP_ENDERECO=0x10001C08`. O gravador verifica se o manifesto
ou o rodapé declara a base do quadro em 0x10001C00.
A liberação para gravação física ainda depende de confirmar WROTP em unidades
separadas no bootloader da revisão usada, em uma unidade de engenharia.

## Registro binário, formato 1

A base B é `0x10001C00`, e o último byte é `0x10001C5F`.
Os inteiros de vários bytes usam little-endian.

| Offset | Tamanho | Conteúdo |
| --- | ---: | --- |
| `0x00` | 1 | Versão do quadro, `0x01` |
| `0x01` | 1 | Tamanho total, `0x60` (96 bytes) |
| `0x02` | 2 | Versão inicial do firmware em BCD. A versão 900 ocupa `00 09` |
| `0x04` | 4 | Identificador ASCII `EEPR` |
| `0x08` | 32 | Chave fixa, na ordem dos pares hexadecimais |
| `0x28` | 16 | Modelo ASCII, com preenchimento `00` à direita |
| `0x38` | 2 | Flash nominal em KiB, 128 ou 256 |
| `0x3A` | 2 | RAM nominal em KiB, 16 ou 64 |
| `0x3C` | 20 | Data e hora de São Paulo (`America/Sao_Paulo`) em ASCII `AAAA-MM-DDTHH:MM:SS`, seguida pelo byte `00` |
| `0x50` | 4 | CRC-32/ISO-HDLC sobre os offsets `0x00–0x4F` |
| `0x54` | 4 | Complemento bit a bit do CRC-32 |
| `0x58` | 8 | Marcador ASCII `CONFOTP1` |

O manifesto legado usa uma versão inteira de 0 a 9999, por exemplo `900`.
O CRC equivale a `zlib.crc32(registro[:80])`. A variante vem da conferência
feita na estação. O CB tem 128 KiB de flash e 16 KiB de RAM. O SE tem
256 KiB de flash e 64 KiB de RAM. A data registra o provisionamento inicial
da OTP, antes da gravação da flash. Quadros antigos com timestamp UTC terminado
em `Z` continuam válidos.

O gravador lê os 96 bytes completos. Uma faixa totalmente `FF` é VAZIA.
VÁLIDO exige todos os campos, data e BCD válidos, capacidades compatíveis com
o modelo, CRC, complemento, marcador e uma chave diferente de 32 bytes
zero ou `FF`. Qualquer outro conteúdo é INVÁLIDO/INCOMPLETO, inclusive
quadros experimentais de 72 bytes. Uma leitura curta interrompe a operação.

O gravador programa as unidades de oito bytes em ordem crescente, até
o offset `0x50`, e pula unidades totalmente `FF`. Antes de escrever
`0x58`, confere os 88 bytes do corpo e que o marcador continua apagado.
Depois relê os 96 bytes. Registros válidos compatíveis são preservados,
incluindo a versão inicial e a data, mesmo se a primeira gravação da flash falhar.

O algoritmo detecta interrupções que deixam diferenças legíveis na OTP. Um
corte antes de qualquer mudança legível é indistinguível de uma região vazia.
Um corte após a programação integral do marcador pode deixar um registro
válido mesmo sem resposta do bootloader. Em ambos os casos, a próxima execução
faz a classificação pela leitura integral. Um registro incompleto requer
tratamento pela fabricação. A ferramenta não tenta completar o registro.
O fluxo não oferece garantia de atomicidade do hardware.

## Estação e pacote de produção

1. Gere o binário combinado de produção para a variante e o endereço aprovados.
   Publique com ele um manifesto JSON controlado pelo processo de release. A
   ferramenta confia no manifesto para declarar as opções de compilação. O
   SHA-256 verifica que os bytes gravados são os bytes declarados pelo release.
2. Inclua no manifesto `mcu` (`ASR6601CB` ou `ASR6601SE`), `otp_base`
   (`"0x10001C00"`), `otp_formato` (inteiro 1),
   `versao` no formato acima e
   `sha256` com 64 dígitos hexadecimais minúsculos do binário combinado.

3. Confira a variante na marcação física ou no cadastro de fabricação antes de
   passá-la ao gravador. A variante informada deve coincidir com a do manifesto.
   O gravador lê e registra automaticamente o serial da unidade conectada à porta
   informada. Se necessário, use `--serial-producao` com os 16 dígitos hexadecimais
   esperados para exigir correspondência antes de acessar a OTP. O comando legado
   `identificar_mcu` usa tentativas de apagar EEPROM e fica fora do fluxo.
4. Instale a versão atualizada do gravador na estação. No firmware, os alvos
   `flash_producao`, `producao` e `producao_cripto` exigem as variáveis
   `MANIFESTO_PRODUCAO` e `MCU_PRODUCAO`. `SERIAL_PRODUCAO` é opcional.
   A estação também pode chamar o gravador diretamente:

   ```powershell
   $env:ASR_ARQUIVO_CHAVE_EEPROM = Read-Host 'Caminho do arquivo da chave'
   $varianteAsr = Read-Host 'Variante conferida na unidade (ASR6601CB ou ASR6601SE)'
   .\.venv\Scripts\python.exe .\asr_loader.py -p COM3 --log-file producao.log flash --producao manifesto.json --mcu $varianteAsr 0x08000000 producao.bin
   ```

O comando valida o vetor de boot, a faixa da flash, a variante declarada,
o manifesto e a chave antes da conexão. Preserva as páginas de
4 KiB em `0x0801E000–0x0801FFFF` (CB) ou `0x0803E000–0x0803FFFF` (SE).
Só usa ERASE e FLASH para o binário combinado após confirmar a OTP. As
configurações de proteção, depuração e Option Bytes permanecem fora do fluxo.
Os comandos diagnósticos brutos `ler_otp` e `escrever_otp` do Makefile não
devem ser usados com a reserva da EEPROM. Eles expõem dados por saída ou
argumentos de processo.

### Ensaio de bancada somente leitura

Para comparar o comportamento da flash no limite de 128 KiB em unidades CB e
SE conhecidas, execute:

```powershell
.\.venv\Scripts\python.exe .\asr_loader.py -p COM3 diagnosticar_flash_asr
```

O comando usa RDREG para comparar cinco palavras no início da flash com as
posições correspondentes 128 KiB acima. Relata falha na leitura superior,
leituras iguais, janela superior com `FF` ou leituras distintas. Repita em
placas de ambas as variantes e anote a revisão do bootloader. A sondagem
não programa nem apaga memória. Um erro acima de 128 KiB pode ter outras
causas, como proteção de leitura, e o resultado ainda não substitui
`--mcu`.

Em uma unidade de bancada destinada à regravação, habilite o ensaio de
escrita explicitamente com o serial esperado:

```powershell
$serialAsr = Read-Host 'Serial da unidade de teste'
.\.venv\Scripts\python.exe .\asr_loader.py -p COM3 diagnosticar_flash_asr --testar-escrita $serialAsr
```

O comando confirma pelo CRC que as páginas de 4 KiB em `0x08002000` e
`0x08022000` estão apagadas. A primeira é a posição que corresponderia a um
espelhamento de 128 KiB. Depois grava oito bytes de teste na página superior
e confirma por CRC que eles ficaram nessa página e que a inferior permaneceu
apagada. Se confirmar a escrita independente, apaga a página de teste e
verifica novamente ambas as páginas. O resultado positivo é compatível com
SE. Uma falha é inconclusiva e, se ocorreu após o envio da escrita, o
padrão pode permanecer na flash até a regravação da unidade. O teste fica
fora da gravação de produção e não acessa OTP ou páginas da EEPROM.

Para levantar faixas candidatas antes de ter manifesto ou binário,
execute, na raiz do gravador:

```powershell
.\.venv\Scripts\python.exe .\asr_loader.py -p COM3 diagnosticar_otp
```

O diagnóstico lê os 1.024 bytes em dois blocos, informa o serial do chip e
mostra apenas intervalos alinhados de pelo menos 96 bytes que retornaram
`FF`. Ele usa a conexão com o bootloader e fecha a porta após a leitura.
Uma faixa que retorna `FF` pode estar reservada para outro uso. A fabricação
precisa aprová-la antes de usá-la.

Use o mesmo binário, manifesto, variante e chave previstos para a
produção. Acrescente `--somente-validar` ao comando:

```powershell
$env:ASR_ARQUIVO_CHAVE_EEPROM = Read-Host 'Caminho do arquivo da chave'
$varianteAsr = Read-Host 'Variante conferida na unidade (ASR6601CB ou ASR6601SE)'
.\.venv\Scripts\python.exe .\asr_loader.py -p COM3 flash --somente-validar --producao manifesto.json --mcu $varianteAsr 0x08000000 producao.bin
```

Execute o exemplo na raiz do gravador e ajuste `COM3` e os caminhos aos
arquivos reais da estação. Para consultar o número de série, use
`.\.venv\Scripts\python.exe .\asr_loader.py -p COM3 serial` e confronte o
valor exibido com o cadastro do equipamento.

O gravador valida os insumos, identifica o equipamento, lê os 96 bytes e
informa o estado sem exibir os dados brutos. O código de saída é 0 para
`VAZIO` ou `VÁLIDO` com a chave esperada. Uma chave diferente, um registro
`INVÁLIDO/INCOMPLETO` ou uma falha de validação ou comunicação retorna 1.
O modo fecha a porta sem programar OTP, apagar ou gravar flash, alterar
Option Bytes ou enviar o comando de reinicialização do bootloader.

A conexão pode usar DTR/RTS para colocar o equipamento no bootloader.
Se o equipamento já estiver no bootloader e o objetivo for evitar esse reset,
adicione `--no-auto-boot` antes de `flash`. O ensaio confirma a comunicação
e o estado legível da faixa. A confirmação da granularidade de WROTP requer
um ensaio separado com uma unidade de engenharia e uma faixa autorizada.

### Equipamentos novos, já provisionados e legados

- **Novos** — use o fluxo de produção com o binário inicial e
  `EEPROM_PERMITIR_MIGRACAO=0`. A OTP é confirmada antes da gravação do binário.
- **Já provisionados** — na bancada, repita o fluxo de produção para validar e
  preservar o registro, inclusive depois de falha na flash. Em campo, use a
  atualização OTA compatível, que preserva OTP e EEPROM. Valide no release o
  mesmo endereço e formato e os limites do bootloader que instala a atualização.
  Forneça o arquivo da chave apenas durante a sessão de produção.
- **Legados com imagens CRC** — leve à estação, confirme a reserva e preserve
  ambas as páginas. Em uma unidade sem registro, o primeiro firmware registrado
  será o da migração. Compile com `EEPROM_PERMITIR_MIGRACAO=1`, provisione e
  grave pelo fluxo de produção. Confirme no boot a migração das duas páginas.
  Depois, instale firmware com `EEPROM_PERMITIR_MIGRACAO=0`. Uma unidade que
  já contém somente a chave na faixa reservada é classificada como incompleta.
  Imagens antigas em formato bruto anterior ao CRC exigem tratamento separado.

## Contrato para o firmware consumidor

Compile com `EEPROM_CHAVE_OTP_ENDERECO=B+0x08`. Para validar o registro no
firmware, estenda `eeprom_seguranca.h` para exigir alinhamento e que
`B+96 <= 0x10002000`, e altere `eeprom_obter_chave()` em `eeprom.c`.
Leia o registro inteiro, valide marcador, identificador, formato, tamanho,
versão BCD, data, chave não trivial, CRC, complemento e a correspondência de variante e capacidades.
Decodifique
inteiros explicitamente em little-endian. Só então copie os 32 bytes de
`B+0x08` para o buffer de chave. Retorne falha na ausência de registro
válido antes da inicialização ou cifragem da EEPROM. Limpe buffers temporários
pela rotina de limpeza já usada pela cifra. Preserve o caminho de testes host
com chave fictícia e acrescente vetores de registro válido, incompleto e
corrompido. A validação é de leitura. A versão inicial é informação de
fabricação e não seleciona a chave.

O `eeprom_obter_chave()` atual lê somente os 32 bytes e rejeita chave toda
zero ou toda `FF`. O gravador valida o registro completo. A alteração do
consumidor é uma pendência de integração antes da liberação do produto.
Nenhuma validação física de OTP foi executada no desenvolvimento.
