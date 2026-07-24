"""Ponto de entrada compatível para o ASR Loader."""

import sys

VERSAO_GRAVADOR = "1.3"

from src.cli import main

if __name__ == '__main__':
    sys.exit(main())
