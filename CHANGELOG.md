## v102 - Unreleased

- Estruturação modular da aplicação em `src/`, separando CLI, comandos, protocolo, constantes, utilitários e runtime.
- Fluxo principal de uso mantido: descoberta de portas, conexão, envio de comandos e validações básicas da CLI.
- `tremo_loader.py` mantido como ponto de entrada compatível, delegando execução para `src/cli.py`.
- Interface de linha de comando preservada (comandos e flags existentes continuam disponíveis).
- Nova abstração de comunicação serial em `src/serial_port.py` com a classe `SerialPort`.
- `src/protocolo.py` deixou de depender diretamente de `pyserial` e passou a usar `SerialPort`.
- Operações de controle de linha e buffers (`DTR/RTS`, flush de entrada/saída) foram centralizadas na abstração serial.
