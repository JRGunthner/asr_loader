@echo off
echo ====================================================
echo    TREMO LOADER - Atualizar Build Tools
echo    Atualiza os tremos de acordo com os arquivos
echo    de build mais recentes nas pastas dos firmwares
echo ====================================================
echo.

@echo off
echo ===============================================
echo    BUILD
echo ===============================================
echo.
REM Ativar ambiente virtual se existir
if exist .venv\Scripts\activate.bat (
    echo Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
)

REM Executar o script do build
python build.py
echo ===============================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "SOURCE_EXE="
set "SOURCE_MANUAL=%SCRIPT_DIR%README.md"

if not exist "%DIST_DIR%\" (
	echo ERRO: pasta dist nao encontrada em "%DIST_DIR%"
	exit /b 1
)

if not exist "%SOURCE_MANUAL%" (
	echo ERRO: arquivo README.md nao encontrado em "%SOURCE_MANUAL%"
	exit /b 1
)

for /f "delims=" %%F in ('dir /b /a:-d /o-d "%DIST_DIR%\tremo-loader-v*.exe" 2^>nul') do (
	set "SOURCE_EXE=%DIST_DIR%\%%F"
	goto :source_found
)

echo ERRO: nenhum arquivo "tremo-loader-v*.exe" foi encontrado em "%DIST_DIR%"
exit /b 1

:source_found
echo Build encontrado: "%SOURCE_EXE%"
echo.

call :copy_to "D:\projetos\pr439v1-postyou-dlms\tools"
if errorlevel 1 exit /b 1
call :copy_to "D:\projetos\pr439v2-postyou-dlms\tools"
if errorlevel 1 exit /b 1
call :copy_to "D:\projetos\pr413v6-postyou-abnt\tools"
if errorlevel 1 exit /b 1

echo.
echo Atualizacao concluida.
exit /b 0

:copy_to
set "TARGET_DIR=%~1"

if not exist "%TARGET_DIR%\" (
	echo AVISO: pasta de destino nao encontrada: "%TARGET_DIR%"
	goto :eof
)

copy /Y "%SOURCE_EXE%" "%TARGET_DIR%\tremo_loader.exe" >nul
if errorlevel 1 (
	echo ERRO: falha ao copiar para "%TARGET_DIR%\tremo_loader.exe"
	exit /b 1
)

copy /Y "%SOURCE_MANUAL%" "%TARGET_DIR%\MANUAL_tremo_loader.md" >nul
if errorlevel 1 (
	echo ERRO: falha ao copiar para "%TARGET_DIR%\MANUAL_tremo_loader.md"
	exit /b 1
)

echo Copiado para "%TARGET_DIR%\tremo_loader.exe"
echo Copiado para "%TARGET_DIR%\MANUAL_tremo_loader.md"
goto :eof
