## v1.3 - Unreleased
- Adição do comando para gerar a versão de firmware OTA
- Adicionado endereço da eeprom do ASR6601SE
- Correção do bug da mensagem de erro de gravação sempre concluída
- Durante `flash`, o apagamento de EEPROM não exibe erro de mapeamento ausente e passa a informar o mapeamento/chip detectado.
- Durante `flash`, identifica o chip (`ASR6601CB ou ASR6601SE`).
- Novo script `atualizar-builds.bat` copia automaticamente o executável versionado mais recente de `dist\tremo_loader-v*.exe` para as pastas de tools dos projetos com ASR.
- Adição do comando `ota_assinado` para gerar pacote OTA assinado com `--firmware-version` e `--key-header`.
- `atualizar-builds.bat` agora gera `MANUAL_tremo_loader.md` com a versão e a data do último executável encontrado em `dist`, preenchidas automaticamente a partir do `README.md`.

## v1.2 - 2025-10-07
- Estruturação modular da aplicação em `src/`, separando CLI, comandos, protocolo, constantes, utilitários e runtime.
- Fluxo principal de uso mantido: descoberta de portas, conexão, envio de comandos e validações básicas da CLI.
- `tremo_loader.py` mantido como ponto de entrada compatível, delegando execução para `src/cli.py`.
- Interface de linha de comando preservada (comandos e flags existentes continuam disponíveis).
- Nova abstração de comunicação serial em `src/serial_port.py` com a classe `SerialPort`.
- `src/protocolo.py` deixou de depender diretamente de `pyserial` e passou a usar `SerialPort`.
- Operações de controle de linha e buffers (`DTR/RTS`, flush de entrada/saída) foram centralizadas na abstração serial.
- Release
