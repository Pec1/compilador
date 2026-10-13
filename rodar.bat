@echo off
rem Uso: rodar.bat arquivo.java [--json] [--ascii] [--sem-fonte]
rem Procura o Python pelo launcher "py" e, se nao houver, pelo comando "python".
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
    echo Uso: rodar.bat arquivo.java [--json] [--ascii] [--sem-fonte]
    exit /b 1
)
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 main.py %*
    exit /b %errorlevel%
)
python --version >nul 2>&1
if not errorlevel 1 (
    python main.py %*
    exit /b %errorlevel%
)
echo [ERRO] Python nao encontrado. Instale o Python 3.7+ em https://www.python.org/downloads/
echo        marcando a opcao "Add python.exe to PATH".
exit /b 1
