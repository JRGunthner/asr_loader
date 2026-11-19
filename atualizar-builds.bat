@echo off
echo ====================================================
echo    ASR LOADER - Atualizar Build Tools
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
set "RENDERED_MANUAL=%TEMP%\MANUAL_asr_loader_%RANDOM%%RANDOM%.md"

if not exist "%DIST_DIR%\" (
	echo ERRO: pasta dist nao encontrada em "%DIST_DIR%"
	exit /b 1
)

if not exist "%SOURCE_MANUAL%" (
	echo ERRO: arquivo README.md nao encontrado em "%SOURCE_MANUAL%"
	exit /b 1
)

for /f "delims=" %%F in ('dir /b /a:-d /o-d "%DIST_DIR%\asr-loader-v*.exe" 2^>nul') do (
	set "SOURCE_EXE=%DIST_DIR%\%%F"
	goto :source_found
)

echo ERRO: nenhum arquivo "asr-loader-v*.exe" foi encontrado em "%DIST_DIR%"
exit /b 1

:source_found
echo Build encontrado: "%SOURCE_EXE%"
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
	"$exe = Get-Item -LiteralPath '%SOURCE_EXE%';" ^
	"$readme = Get-Content -LiteralPath '%SOURCE_MANUAL%' -Raw -Encoding UTF8;" ^
	"$version = if ($exe.BaseName -match 'asr-loader-v(.+)$') { $Matches[1] } else { $exe.BaseName };" ^
	"$buildDate = $exe.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss');" ^
	"$manual = $readme.Replace('{{BUILD_VERSION}}', $version).Replace('{{BUILD_DATE}}', $buildDate);" ^
	"Set-Content -LiteralPath '%RENDERED_MANUAL%' -Value $manual -Encoding Default"
if errorlevel 1 (
  echo ERRO: falha ao gerar MANUAL_asr_loader.md a partir do README.md
  exit /b 1
)

call :copy_to "D:\projetos\pr439v1-postyou-dlms\tools"
if errorlevel 1 exit /b 1
call :copy_to "D:\projetos\pr439v2-postyou-dlms\tools"
if errorlevel 1 exit /b 1
call :copy_to "D:\projetos\pr439v3-postyou-dlms\tools"
if errorlevel 1 exit /b 1
call :copy_to "D:\projetos\pr413v6-postyou-abnt\tools"
if errorlevel 1 exit /b 1

echo.
echo Atualizacao concluida.
if exist "%RENDERED_MANUAL%" del /q "%RENDERED_MANUAL%" >nul 2>nul
exit /b 0

:copy_to
set "TARGET_DIR=%~1"

if not exist "%TARGET_DIR%\" (
	echo AVISO: pasta de destino nao encontrada: "%TARGET_DIR%"
	goto :eof
)

copy /Y "%SOURCE_EXE%" "%TARGET_DIR%\asr_loader.exe" >nul
if errorlevel 1 (
	echo ERRO: falha ao copiar para "%TARGET_DIR%\asr_loader.exe"
	exit /b 1
)

copy /Y "%RENDERED_MANUAL%" "%TARGET_DIR%\MANUAL_asr_loader.md" >nul
if errorlevel 1 (
	echo ERRO: falha ao copiar para "%TARGET_DIR%\MANUAL_asr_loader.md"
	exit /b 1
)

echo Copiado para "%TARGET_DIR%\asr_loader.exe"
echo Copiado para "%TARGET_DIR%\MANUAL_asr_loader.md"
goto :eof
