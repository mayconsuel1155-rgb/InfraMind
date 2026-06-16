@echo off
title InfraMind - Inicializador do Sistema
chcp 65001 > nul
cls

echo ============================================================
echo                 INFRAMIND - SISTEMA DE MONITORAMENTO
echo ============================================================
echo.
echo Escolha o método de inicialização desejado:
echo.
echo [1] Iniciar com Docker - Banco Postgres + Backend na Porta 8000
echo [2] Iniciar sem Docker - Modo Manual com SQLite/Local
echo [3] Sair
echo.
set /p opcao="Digite a opção desejada (1-3): "

if "%opcao%"=="1" goto docker
if "%opcao%"=="2" goto local
if "%opcao%"=="3" goto sair
goto erro

:docker
echo.
echo ============================================================
echo          VERIFICANDO DAEMON DO DOCKER
echo ============================================================
echo.

:: Verificar se Docker está instalado
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Erro: O comando 'docker' não foi encontrado no PATH.
    echo [!] Por favor, instale o Docker Desktop.
    pause
    goto sair
)

:: Verificar se o daemon está rodando
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Docker daemon já está em execução.
    goto docker_ready
)

echo [-] Docker Desktop não está em execução. Tentando iniciar automaticamente...
if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" goto docker_not_found

start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo [*] Iniciando Docker Desktop. Aguardando inicialização do daemon...

set count=0

:wait_docker_start
timeout /t 3 > nul
set /a count+=3
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Docker daemon conectado com sucesso!
    goto docker_ready
)
if %count% geq 60 goto docker_timeout
echo [*] Aguardando daemon do Docker... %count%s de 60s
goto wait_docker_start

:docker_timeout
echo [-] Tempo limite atingido. O Docker Desktop não iniciou a tempo.
echo [!] Abra o Docker Desktop manualmente e execute o script novamente.
pause
goto sair

:docker_not_found
echo [-] Caminho padrão do Docker Desktop.exe não encontrado.
echo [!] Por favor, inicie o Docker Desktop manualmente e tente de novo.
pause
goto sair

:docker_ready
echo.
echo [+] Iniciando containers com Docker Compose...
docker compose up --build
pause
goto sair

:local
echo.
echo [+] Iniciando no modo local nativo...
if not exist "venv\Scripts\activate.bat" (
    echo [-] Ambiente virtual venv não encontrado na pasta raiz.
    echo [-] Por favor, execute o script 'instalar_servidor.bat' primeiro para configurar.
    pause
    goto sair
)
echo [+] Ativando ambiente virtual...
call venv\Scripts\activate.bat
echo [+] Iniciando servidor Django na porta 8000...
python backend\manage.py runserver
pause
goto sair

:erro
echo.
echo [-] Opção inválida! Escolha 1, 2 ou 3.
pause
cls
goto :EOF

:sair
echo.
echo Obrigado por usar o InfraMind. Fechando...
timeout /t 3 > nul
exit
