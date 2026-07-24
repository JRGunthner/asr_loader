import subprocess
import sys
from pathlib import Path


def executar_testes():
    raiz_projeto = Path(__file__).resolve().parent.parent
    python_projeto = raiz_projeto / '.venv' / 'Scripts' / 'python.exe'
    pasta_testes = raiz_projeto / 'tests'

    if not python_projeto.exists():
        print('Erro: ambiente virtual não encontrado em .venv.')
        print('Crie o ambiente e instale as dependências antes de executar os testes.')
        return 1

    comando = [
        str(python_projeto),
        '-m',
        'pytest',
        str(pasta_testes),
        *sys.argv[1:],
    ]
    return subprocess.call(comando, cwd=raiz_projeto)


if __name__ == '__main__':
    raise SystemExit(executar_testes())
