@echo off
title InfraMind - Instalador do Servidor
chcp 65001 > nul
cls

echo ============================================================
echo                 INFRAMIND - INSTALAÇÃO E CONFIGURAÇÃO
echo ============================================================
echo.
echo Escolha o tipo de instalação desejada:
echo.
echo [1] Instalação com Docker - Recomendado - Banco Postgres
echo [2] Instalação sem Docker - Modo Local - Banco SQLite
echo [3] Sair
echo.
set /p tipo_instala="Digite a opção desejada (1-3): "

if "%tipo_instala%"=="1" goto instalar_docker
if "%tipo_instala%"=="2" goto instalar_local
if "%tipo_instala%"=="3" goto sair
goto erro_opcao

:instalar_docker
echo.
echo ============================================================
echo          CONFIGURANDO AMBIENTE COM DOCKER
echo ============================================================
echo.

:: Verificar se Docker está instalado
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Erro: O comando 'docker' não foi encontrado no PATH.
    echo [!] Instale o Docker Desktop antes de prosseguir com esta opção.
    pause
    exit /b
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

:wait_docker
timeout /t 3 > nul
set /a count+=3
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Docker daemon conectado com sucesso!
    goto docker_ready
)
if %count% geq 60 goto docker_timeout
echo [*] Aguardando daemon do Docker... %count%s de 60s
goto wait_docker

:docker_timeout
echo [-] Tempo limite de 60 segundos atingido. O Docker não carregou a tempo.
echo [!] Abra o Docker Desktop manualmente e execute este script de novo.
pause
exit /b

:docker_not_found
echo [-] Caminho padrão do Docker Desktop.exe não encontrado.
echo [!] Por favor, inicie o Docker Desktop manualmente e execute este script de novo.
pause
exit /b

:docker_ready
echo.
:: Configurar arquivo .env sem usar blocos de parênteses aninhados
if exist "backend\.env" goto env_docker_exists
echo [+] Criando arquivo backend\.env...
copy backend\.env.example backend\.env > nul

echo [+] Gerando chaves criptográficas seguras...
python --version >nul 2>&1
if %errorlevel% neq 0 goto no_python_docker
python -c "import secrets; from cryptography.fernet import Fernet; path='backend/.env'; data=open(path, 'r', encoding='utf-8').read(); data=data.replace('django-insecure-your-secret-key-here', secrets.token_urlsafe(50)).replace('t-cBRv8E_YpZg8Yq4Jt1s0z-l3eYgG67_3N421kL8k0=', Fernet.generate_key().decode()); open(path, 'w', encoding='utf-8').write(data)"
goto env_docker_exists

:no_python_docker
echo [!] Aviso: Python local não detectado para gerar chaves seguras.
echo [!] O .env usará chaves provisórias. Altere-as depois no arquivo.

:env_docker_exists
echo.
echo [+] Construindo e iniciando containers com Docker Compose...
docker compose up --build -d
if %errorlevel% neq 0 (
    echo [-] Erro ao rodar docker compose up.
    pause
    exit /b
)

echo.
echo ============================================================
echo [+] INSTALAÇÃO DOCKER CONCLUÍDA COM SUCESSO!
echo ============================================================
echo.
echo O sistema está rodando em segundo plano.
echo Acesse no seu navegador: http://localhost:8000
echo.
echo Credenciais padrões de acesso geradas:
echo   - Usuário: admin@inframind.com
echo   - Senha: AdminPassword123!
echo.
pause
goto sair

:instalar_local
echo.
echo ============================================================
echo          CONFIGURANDO AMBIENTE LOCAL NATIVO - SQLITE
echo ============================================================
echo.

:: Verificar se Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Erro: Python não foi encontrado no sistema.
    echo [+] Por favor, instale o Python 3.11+ e adicione-o ao PATH.
    pause
    exit /b
)

:: Criar ambiente virtual
if not exist "venv" (
    echo [+] Criando ambiente virtual venv...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [-] Falha ao criar venv.
        pause
        exit /b
    )
)

echo [+] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo [+] Atualizando o pip...
python -m pip install --upgrade pip

echo [+] Instalando dependências do backend...
pip install -r backend\requirements\development.txt
if %errorlevel% neq 0 (
    echo [-] Erro ao instalar dependências.
    pause
    exit /b
)

:: Configurar o arquivo .env sem blocos de parênteses
if exist "backend\.env" goto env_local_exists
echo [+] Arquivo backend\.env não encontrado. Copiando do exemplo...
copy backend\.env.example backend\.env > nul

echo [+] Gerando chaves criptográficas seguras...
python -c "import secrets; from cryptography.fernet import Fernet; path='backend/.env'; data=open(path, 'r', encoding='utf-8').read(); data=data.replace('django-insecure-your-secret-key-here', secrets.token_urlsafe(50)).replace('t-cBRv8E_YpZg8Yq4Jt1s0z-l3eYgG67_3N421kL8k0=', Fernet.generate_key().decode()); open(path, 'w', encoding='utf-8').write(data)"
echo [+] Chaves gravadas em backend\.env com sucesso.

:env_local_exists
echo.
:: Executar migrações do banco
echo [+] Executando migrações do banco de dados SQLite...
python backend\manage.py migrate
if %errorlevel% neq 0 (
    echo [-] Erro ao executar migrações.
    pause
    exit /b
)

:: Criar Superusuário
echo ============================================================
echo DESEJA CRIAR UM SUPERUSUÁRIO AGORA? - Administrador Geral
echo ============================================================
echo.
set /p criar_admin="Criar superusuário? (S/N): "
if /i "%criar_admin%"=="S" (
    echo [+] Iniciando criação de superusuário...
    python backend\manage.py createsuperuser
)
echo.

echo ============================================================
echo [+] INSTALAÇÃO LOCAL CONCLUÍDA COM SUCESSO!
echo ============================================================
echo.
echo Para iniciar o sistema local, execute o script 'iniciar_sistema.bat' na raiz do projeto.
echo.
pause
goto sair

:erro_opcao
echo.
echo [-] Opção inválida! Escolha 1, 2 ou 3.
pause
cls
goto :EOF

:sair
echo.
exit
