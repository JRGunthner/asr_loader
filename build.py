#!/usr/bin/env python3
"""
Script para compilar o ASR Loader com PyInstaller
Gera o executável com nome versionado automaticamente
A versao é extraída do código fonte
Cria uma cópia do executável na pasta teste-build para testes rápidos
Limpa builds anteriores de forma segura
Testa o executável gerado e mostra informações úteis
Requer Python 3.6+ e PyInstaller
"""

import os
import sys
import subprocess
import re
import shutil
import time
from datetime import datetime


### @brief Extrai a versão do código fonte e cria o executável com PyInstaller
### @return Versão extraída ou "100" se não encontrada
def extrair_versao():
    try:
        with open('asr_loader.py', 'r', encoding='utf-8') as f:
            conteudo = f.read()

        match = re.search(r'VERSAO_GRAVADOR\s*=\s*["\']([^"\']+)["\']', conteudo)
        if match:
            return match.group(1)
        else:
            print("⚠️  VERSAO_GRAVADOR não encontrada, usando versão padrão '100'")
            return "100"
    except FileNotFoundError:
        print("❌ Arquivo asr_loader.py não encontrado!")
        sys.exit(1)


### @brief Executa um comando de shell e trata erros
### @param  comando Comando a ser executado
### @param  descricao Descrição do que o comando faz (para logs)
### @return True se o comando foi executado com sucesso, False caso contrário
def executar_comando(comando, descricao):
    print(f"\n🔄 {descricao}...")
    print(f"   Comando: {comando}")

    try:
        subprocess.run(comando, shell=True, check=True, capture_output=True, text=True)
        print("✅ Sucesso!")
        return True
    except subprocess.CalledProcessError as excessao:
        print(f"❌ Erro: {e}")
        if excessao.stderr:
            print(f"   Erro: {excessao.stderr}")
        return False


### @brief Verifica se PyInstaller está instalado, tenta instalar se não estiver
### @return True se PyInstaller está instalado, False caso contrário
def instalar_pyinstaller():
    try:
        subprocess.run(['pyinstaller', '--version'], check=True, capture_output=True)
        print("✅ PyInstaller já instalado")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 PyInstaller não encontrado. Instalando...")
        return executar_comando('pip install pyinstaller', 'Instalando PyInstaller')


### @brief Remove uma pasta de forma segura, tentando várias vezes se necessário
### @param  pasta Caminho da pasta ou arquivo a ser removido
### @return True se a pasta foi removida ou não existia, False se falhou
def remover_pasta_seguro(pasta):
    if not os.path.exists(pasta):
        return True

    print(f"   Removendo {pasta}...")

    for tentativa in range(3):
        try:
            if os.path.isfile(pasta):
                os.remove(pasta)
            else:
                shutil.rmtree(pasta)
            print(f"   ✅ {pasta} removido com sucesso")
            return True
        except PermissionError:
            if tentativa < 2:
                print(f"   ⏳ Tentativa {tentativa + 1}/3 - aguardando...")
                time.sleep(2)
            else:
                print(f"   ⚠️  Não foi possível remover {pasta} (arquivo em uso)")
                return False
        except Exception as excessao:
            print(f"   ⚠️  Erro ao remover {pasta}: {excessao}")
            return False

    return False


### @brief Limpa builds anteriores
def limpar_build_anterior():
    print("\n🧹 Limpando build anterior...")

    pastas = ['build', '__pycache__']

    if os.path.exists('dist'):
        print("   Limpando arquivos antigos em dist...")
        try:
            for arquivo in os.listdir('dist'):
                caminho = os.path.join('dist', arquivo)
                if arquivo.startswith('asr-loader-'):
                    if remover_pasta_seguro(caminho):
                        print(f"   ✅ Removido: {arquivo}")
        except Exception as excessao:
            print(f"   ⚠️  Erro ao limpar dist: {excessao}")

    for pasta in pastas:
        remover_pasta_seguro(pasta)

    try:
        for arquivo in os.listdir('.'):
            if arquivo.endswith('.spec'):
                if remover_pasta_seguro(arquivo):
                    print(f"   ✅ Removido: {arquivo}")
    except Exception as excessao:
        print(f"   ⚠️  Erro ao remover arquivos .spec: {excessao}")


### @brief Cria o executável com PyInstaller
### @param  versao Versão extraída do código fonte
### @return True se o executável foi criado com sucesso, False caso contrário
def criar_executavel(versao):
    nome_exe = f'asr-loader-v{versao}'

    # Garante que o diretório dist existe
    if not os.path.exists('dist'):
        os.makedirs('dist')

    # Comando PyInstaller
    comando = [
        'pyinstaller',
        '--onefile',
        '--name', nome_exe,
        '--console',
        '--clean',
        '--noconfirm',
        '--distpath', 'dist',
        '--workpath', 'build',
        'asr_loader.py'
    ]

    print(f"\n🔄 Criando executável {nome_exe}.exe...")
    print(f"   Comando: {' '.join(comando)}")
    print("   Aguarde, isso pode levar alguns minutos...")

    try:
        # Executa PyInstaller com saída em tempo real
        process = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        print("\n📋 Log do PyInstaller:")
        print("-" * 40)

        logs_executavel = []
        while True:
            linha_log = process.stdout.readline()
            if linha_log == '' and process.poll() is not None:
                break
            if linha_log:
                line = linha_log.strip()
                logs_executavel.append(line)

                # Filtra e mostra apenas linhas importantes
                if any(keyword in line.lower() for keyword in [
                    'analyzing', 'building', 'collecting', 'writing',
                    'creating', 'adding', 'copying', 'warning:', 'error:'
                ]):
                    # Trunca linhas muito longas
                    display_line = line[:80] + "..." if len(line) > 80 else line
                    print(f"   {display_line}")
                elif 'INFO:' in line and any(info in line for info in [
                    'Building EXE', 'Building COLLECT', 'Appending PKG', 'Building Analysis'
                ]):
                    print(f"   ⚙️  {line.split('INFO:')[1].strip()}")

        # Aguarda o processo terminar
        return_code = process.wait()

        print("-" * 40)

        if return_code == 0:
            print("✅ Executável criado com sucesso!")
        else:
            print(f"❌ PyInstaller falhou com código: {return_code}")
            # Mostra as últimas linhas de erro
            print("\n🔍 Últimas linhas do log:")
            for line in logs_executavel[-10:]:
                print(f"   {line}")
            return False

        # Move o arquivo .spec para a pasta dist
        spec_file = f'{nome_exe}.spec'
        if os.path.exists(spec_file):
            spec_dest = os.path.join('dist', spec_file)
            shutil.move(spec_file, spec_dest)
            print(f"✅ Arquivo {spec_file} movido para dist/")

        # Cria cópia do executável na pasta teste-build
        exe_file = f'{nome_exe}.exe'
        exe_source = os.path.join('dist', exe_file)

        if os.path.exists(exe_source):
            # Cria pasta teste-build se não existir
            teste_build_dir = 'teste-build'
            if not os.path.exists(teste_build_dir):
                os.makedirs(teste_build_dir)
                print(f"✅ Pasta {teste_build_dir}/ criada")

            # Copia executável para teste-build
            exe_dest = os.path.join(teste_build_dir, exe_file)
            shutil.copy2(exe_source, exe_dest)
            print(f"✅ Cópia do executável criada em {teste_build_dir}/{exe_file}")

        return True

    except Exception as excessao:
        print(f"❌ Erro ao executar PyInstaller: {excessao}")
        return False


### @brief Mostra informações sobre o build final e testa o executável
### @param  versao Versão extraída do código fonte
### @return True se o executável existe, False caso contrário
def mostrar_resultado(versao):
    nome_exe = f'asr-loader-v{versao}.exe'
    caminho_exe = os.path.join('dist', nome_exe)

    if os.path.exists(caminho_exe):
        tamanho = os.path.getsize(caminho_exe) / (1024 * 1024)
        data_build = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("\n" + "=" * 60)
        print("🎉 BUILD COMPLETO!")
        print("=" * 60)
        print(f"📁 Arquivo: {caminho_exe}")
        print(f"📏 Tamanho: {tamanho:.2f} MB")
        print(f"📅 Data: {data_build}")
        print(f"🔖 Versão: {versao}")
        print("=" * 60)

        print("\n🧪 Testando executável...")
        test_cmd = f'"{caminho_exe}" versao'
        try:
            result = subprocess.run(test_cmd, shell=True, check=True, capture_output=True, text=True, timeout=10)
            print("✅ Executável funcionando corretamente!")
            if result.stdout:
                print(f"   Saída: {result.stdout.strip()}")
        except subprocess.TimeoutExpired:
            print("⚠️  Teste do executável demorou muito (possível problema de hardware)")
        except Exception as excessao:
            print(f"⚠️  Não foi possível testar completamente: {excessao}")
            print("   (Isso é normal se não houver dispositivo conectado)")

        return True
    else:
        print(f"\n❌ Erro: Executável não foi criado em {caminho_exe}")
        return False


### @brief Função principal
def main():
    print("🚀 ASR LOADER - BUILD AUTOMÁTICO")
    print("=" * 50)

    # Verifica se estamos no diretório correto
    if not os.path.exists('asr_loader.py'):
        print("❌ Arquivo asr_loader.py não encontrado!")
        print("   Execute este script no diretório do projeto.")
        input("   Pressione Enter para sair...")
        sys.exit(1)

    versao = extrair_versao()
    print(f"🔖 Versão detectada: {versao}")

    if not instalar_pyinstaller():
        print("❌ Falha ao instalar PyInstaller")
        input("   Pressione Enter para sair...")
        sys.exit(1)

    limpar_build_anterior()

    if not criar_executavel(versao):
        print("❌ Falha ao criar executável")
        input("   Pressione Enter para sair...")
        sys.exit(1)

    if mostrar_resultado(versao):
        print("\n🎯 Para distribuir:")
        print(f"   Envie o arquivo: dist/asr-loader-v{versao}.exe")
        print("   É um executável standalone, não precisa instalar nada!")
        print("\n✅ BUILD FINALIZADO COM SUCESSO!")
    else:
        print("❌ BUILD FALHOU")
        input("   Pressione Enter para sair...")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Build cancelado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        input("   Pressione Enter para sair...")
        sys.exit(1)
