@echo off
echo ===============================================
echo    TREMO LOADER - BUILD
echo ===============================================
echo.

REM Ativar ambiente virtual se existir
if exist .venv\Scripts\activate.bat (
    echo Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
)

REM Executar o script do build
python build.py

REM Pausar para ver resultado
echo.
pause
