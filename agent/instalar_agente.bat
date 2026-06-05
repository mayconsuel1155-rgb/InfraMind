@echo off
title InfraMind - Instalador do Agente
chcp 65001 > nul
cls

echo ============================================================
echo                 INFRAMIND - INSTALAÇÃO DO AGENTE
echo ============================================================
echo.

:: Verificar se Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Erro: Python não foi encontrado nesta máquina.
    echo [+] Por favor, instale o Python 3.10+ e marque a opção "Add Python to PATH" durante a instalação.
    pause
    exit /b
)

:: Obter parâmetros da linha de comando
set BACKEND_URL=%~1
set REG_TOKEN=%~2

:: Mudar para o diretório onde o script está localizado
cd /d "%~dp0"

:: Criar venv se não existir
if not exist ".venv" (
    echo [+] Criando ambiente virtual local venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [-] Falha ao criar o ambiente virtual venv.
        pause
        exit /b
    )
)

echo [+] Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo [+] Instalando/Atualizando dependências do agente...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [-] Erro ao instalar as dependências.
    pause
    exit /b
)
echo [+] Dependências instaladas com sucesso.
echo.

:: Executar o agente
if not "%BACKEND_URL%"=="" if not "%REG_TOKEN%"=="" (
    echo [+] Iniciando registro automático silencioso...
    python main.py --backend "%BACKEND_URL%" --token "%REG_TOKEN%"
) else (
    echo [+] Iniciando agente no modo interativo...
    python main.py
)

pause
