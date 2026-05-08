@echo off
REM ota_pack.bat - Empacota firmware para OTA
REM Uso: ota_pack.bat <firmware.bin> [saida.bin]
REM Exemplo: ota_pack.bat ..\release\postyou.bin ..\release\postyou_ota.bin

if "%~1"=="" (
    echo Uso: ota_pack.bat ^<firmware.bin^> [saida.bin]
    exit /b 1
)

python "%~dp0ota_pack.py" %*
