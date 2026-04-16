"""
Arquivo de teste para tremo_loader.py - comando flash
Testa a gravação de firmware no dispositivo ASR6601
"""

import subprocess
import sys
import os

def run_flash_command(address, filename, port=None, baud=921600):
    """
    Executa o comando flash do tremo_loader.py

    Args:
        address: Endereço de memória (ex: "0x08000000")
        filename: Nome do arquivo binário (ex: "0x08000000-main.bin")
        port: Porta serial (opcional, auto-detecta se None)
        baud: Baud rate (padrão: 921600)

    Returns:
        True se sucesso, False se erro
    """
    print(f"\n{'='*60}")
    print(f"Teste de gravação:")
    print(f"  Endereço: {address}")
    print(f"  Arquivo: {filename}")
    print(f"  Porta: {port if port else 'Auto-detectar'}")
    print(f"  Baud rate: {baud}")
    print(f"{'='*60}\n")

    # Monta o comando
    cmd = ["python", "tremo_loader.py"]

    if port:
        cmd.extend(["--port", port])

    cmd.extend(["--baud", str(baud)])
    cmd.extend(["flash", address, filename])

    print(f"Comando: {' '.join(cmd)}\n")

    try:
        # Executa o comando
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # timeout de 2 minutos
        )

        # Mostra a saída
        print("Saída:")
        print(result.stdout)

        if result.stderr:
            print("Erros/Avisos:")
            print(result.stderr)

        # Verifica o resultado
        if result.returncode == 0:
            print("\n✓ Sucesso!")
            return True
        else:
            print(f"\n✗ Falha (código de retorno: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("\n✗ Timeout: O comando demorou mais de 2 minutos")
        return False
    except Exception as e:
        print(f"\n✗ Erro ao executar comando: {e}")
        return False


def test_basic_flash():
    """Teste básico: grava o arquivo principal na memória"""
    print("\n### TESTE 1: Gravação básica ###")
    return run_flash_command(
        address="0x08000000",
        filename="0x08000000-main.bin"
    )


def test_flash_with_port():
    """Teste com porta específica"""
    print("\n### TESTE 2: Gravação com porta específica ###")
    port = input("Digite a porta COM (ex: COM4) ou deixe vazio para pular: ").strip()

    if not port:
        print("Teste pulado.")
        return None

    return run_flash_command(
        address="0x08000000",
        filename="0x08000000-main.bin",
        port=port
    )


def test_flash_custom_baud():
    """Teste com baud rate customizado"""
    print("\n### TESTE 3: Gravação com baud rate diferente ###")
    return run_flash_command(
        address="0x08000000",
        filename="0x08000000-main.bin",
        baud=115200
    )


def test_multiple_files():
    """Teste com múltiplos arquivos (se existirem)"""
    print("\n### TESTE 4: Gravação de múltiplos arquivos ###")

    # Exemplo: gravar múltiplos binários
    # Você pode adicionar mais arquivos conforme necessário
    cmd = [
        "python", "tremo_loader.py",
        "flash",
        "0x08000000", "0x08000000-main.bin"
        # Adicione mais pares endereço/arquivo aqui se necessário
        # "0x08010000", "outro_arquivo.bin"
    ]

    print(f"Comando: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print("Saída:")
        print(result.stdout)

        if result.stderr:
            print("Erros/Avisos:")
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"Erro: {e}")
        return False


def check_prerequisites():
    """Verifica se os arquivos necessários existem"""
    print("\n### Verificação de pré-requisitos ###\n")

    # Verifica se tremo_loader.py existe
    if not os.path.exists("tremo_loader.py"):
        print("✗ tremo_loader.py não encontrado!")
        return False
    else:
        print("✓ tremo_loader.py encontrado")

    # Verifica se o arquivo binário existe
    if not os.path.exists("0x08000000-main.bin"):
        print("✗ 0x08000000-main.bin não encontrado!")
        return False
    else:
        size = os.path.getsize("0x08000000-main.bin")
        print(f"✓ 0x08000000-main.bin encontrado ({size} bytes)")

    # Verifica se pyserial está instalado
    try:
        import serial
        print("✓ pyserial instalado")
    except ImportError:
        print("✗ pyserial não instalado! Execute: pip install pyserial")
        return False

    print("\nTodos os pré-requisitos atendidos!\n")
    return True


def main():
    """Função principal - executa os testes"""
    print("="*60)
    print("TESTES DO TREMO_LOADER.PY - COMANDO FLASH")
    print("="*60)

    # Verifica pré-requisitos
    if not check_prerequisites():
        print("\nPor favor, corrija os problemas acima antes de continuar.")
        sys.exit(1)

    # Menu de testes
    while True:
        print("\n" + "="*60)
        print("MENU DE TESTES")
        print("="*60)
        print("1. Teste básico (auto-detectar porta)")
        print("2. Teste com porta específica")
        print("3. Teste com baud rate diferente (115200)")
        print("4. Teste com múltiplos arquivos")
        print("5. Executar todos os testes")
        print("0. Sair")
        print("="*60)

        choice = input("\nEscolha uma opção: ").strip()

        if choice == "1":
            test_basic_flash()
        elif choice == "2":
            test_flash_with_port()
        elif choice == "3":
            test_flash_custom_baud()
        elif choice == "4":
            test_multiple_files()
        elif choice == "5":
            print("\n### EXECUTANDO TODOS OS TESTES ###")
            test_basic_flash()
            test_flash_with_port()
            test_flash_custom_baud()
            test_multiple_files()
        elif choice == "0":
            print("\nEncerrando testes...")
            break
        else:
            print("\nOpção inválida!")

        input("\nPressione ENTER para continuar...")


if __name__ == "__main__":
    main()

