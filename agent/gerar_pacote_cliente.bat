@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

:: ============================================================
::   InfraMind — Gerador de Pacote de Distribuição
::   Execute este script na máquina do administrador
::   para gerar o instalador pronto para cada empresa.
:: ============================================================

color 0B
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║           InfraMind — Gerador de Pacote Cliente          ║
echo  ║         Crie um instalador pronto por empresa            ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Verificar se o executável do agente existe
if not exist "%~dp0dist\inframind-agent.exe" (
    echo  [ERRO] Executavel nao encontrado em: %~dp0dist\inframind-agent.exe
    echo  Execute primeiro o empacotamento com PyInstaller.
    echo.
    pause
    exit /b 1
)

:: ── Coleta de informações ──────────────────────────────────
echo  Preencha os dados abaixo para gerar o pacote de instalacao:
echo  ─────────────────────────────────────────────────────────
echo.

:: Nome da empresa (usado para nomear a pasta de saída)
set /p COMPANY_NAME="  Nome da Empresa (ex: Empresa ABC): "
if "%COMPANY_NAME%"=="" (
    echo  [ERRO] O nome da empresa e obrigatorio.
    pause & exit /b 1
)

:: URL do backend
set /p BACKEND_URL="  URL do Servidor Backend (ex: http://192.168.0.63:8000): "
if "%BACKEND_URL%"=="" (
    echo  [ERRO] A URL do backend e obrigatoria.
    pause & exit /b 1
)

:: Token de registro da empresa
set /p REG_TOKEN="  Token de Registro da Empresa (obtido no painel): "
if "%REG_TOKEN%"=="" (
    echo  [ERRO] O token de registro e obrigatorio.
    pause & exit /b 1
)

:: Pasta de destino do agente no cliente
set INSTALL_PATH=C:\Program Files\InfraMind
set /p CUSTOM_PATH="  Pasta de instalacao no cliente [%INSTALL_PATH%]: "
if not "%CUSTOM_PATH%"=="" set INSTALL_PATH=%CUSTOM_PATH%

echo.
echo  ─────────────────────────────────────────────────────────
echo  Resumo do pacote a ser gerado:
echo    Empresa  : %COMPANY_NAME%
echo    Backend  : %BACKEND_URL%
echo    Token    : %REG_TOKEN%
echo    Destino  : %INSTALL_PATH%
echo  ─────────────────────────────────────────────────────────
echo.
set /p CONFIRM="  Confirmar e gerar pacote? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo  Operacao cancelada.
    pause & exit /b 0
)

:: ── Criação do pacote ─────────────────────────────────────
:: Sanitiza o nome da empresa para usar como nome de pasta
set "SAFE_NAME=%COMPANY_NAME: =_%"
set "SAFE_NAME=%SAFE_NAME:/=-%"
set "SAFE_NAME=%SAFE_NAME:\=-%"

set "OUT_DIR=%~dp0pacotes\InfraMind_%SAFE_NAME%"

echo.
echo  [*] Criando pasta do pacote: %OUT_DIR%
if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%OUT_DIR%"

:: Copia o executável
echo  [*] Copiando executavel...
copy /y "%~dp0dist\inframind-agent.exe" "%OUT_DIR%\inframind-agent.exe" >nul

:: Copia o ícone (se existir)
if exist "%~dp0inframind-agent.ico" (
    copy /y "%~dp0inframind-agent.ico" "%OUT_DIR%\inframind-agent.ico" >nul
)

:: Gera o config.json pré-configurado com o token
echo  [*] Gerando config.json com token da empresa...
(
    echo {
    echo     "backend_url": "%BACKEND_URL%",
    echo     "registration_token": "%REG_TOKEN%"
    echo }
) > "%OUT_DIR%\config.json"

:: Gera o script instalador para o cliente
echo  [*] Gerando instalador para o cliente...
(
    echo @echo off
    echo setlocal EnableDelayedExpansion
    echo chcp 65001 ^>nul 2^>^&1
    echo.
    echo :: Verifica privilegios de administrador
    echo net session ^>nul 2^>^&1
    echo if %%errorlevel%% neq 0 ^(
    echo     echo [ERRO] Execute este instalador como Administrador^^!
    echo     echo Clique com botao direito em instalar.bat e escolha "Executar como administrador"
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo color 0B
    echo cls
    echo echo.
    echo echo  ╔══════════════════════════════════════════════════════════╗
    echo echo  ║         InfraMind Agent — Instalador Automatico          ║
    echo echo  ║              Empresa: %COMPANY_NAME%
    echo echo  ╚══════════════════════════════════════════════════════════╝
    echo echo.
    echo echo  [*] Instalando agente de monitoramento InfraMind...
    echo echo      Servidor : %BACKEND_URL%
    echo echo      Empresa  : %COMPANY_NAME%
    echo echo.
    echo.
    echo :: Cria pasta de instalacao
    echo set "INSTALL_DIR=%INSTALL_PATH%"
    echo echo  [*] Criando pasta de instalacao: %%INSTALL_DIR%%
    echo if not exist "%%INSTALL_DIR%%" mkdir "%%INSTALL_DIR%%"
    echo.
    echo :: Encerra processo existente do agente (se houver)
    echo echo  [*] Verificando processos existentes...
    echo taskkill /f /im inframind-agent.exe ^>nul 2^>^&1
    echo timeout /t 2 /nobreak ^>nul
    echo.
    echo :: Copia os arquivos
    echo echo  [*] Copiando arquivos do agente...
    echo copy /y "%%~dp0inframind-agent.exe" "%%INSTALL_DIR%%\inframind-agent.exe" ^>nul
    echo copy /y "%%~dp0config.json" "%%INSTALL_DIR%%\config.json" ^>nul
    echo if exist "%%~dp0inframind-agent.ico" copy /y "%%~dp0inframind-agent.ico" "%%INSTALL_DIR%%\inframind-agent.ico" ^>nul
    echo.
    echo :: Remove tarefa agendada anterior (se existir)
    echo echo  [*] Configurando inicializacao automatica com o Windows...
    echo schtasks /delete /tn "InfraMindAgent" /f ^>nul 2^>^&1
    echo.
    echo :: Cria tarefa agendada para iniciar com o Windows (conta SYSTEM)
    echo schtasks /create /tn "InfraMindAgent" /tr "\"%%INSTALL_DIR%%\inframind-agent.exe\"" /sc onstart /ru "SYSTEM" /rl highest /f ^>nul
    echo.
    echo if %%errorlevel%% equ 0 ^(
    echo     echo  [OK] Tarefa agendada criada com sucesso^^!
    echo ^) else ^(
    echo     echo  [AVISO] Falha ao criar tarefa agendada. Configure manualmente se necessario.
    echo ^)
    echo.
    echo :: Inicia o agente imediatamente
    echo echo  [*] Iniciando agente de monitoramento...
    echo start "" "%%INSTALL_DIR%%\inframind-agent.exe"
    echo timeout /t 3 /nobreak ^>nul
    echo.
    echo :: Verifica se o processo está rodando
    echo tasklist /fi "imagename eq inframind-agent.exe" 2^>nul ^| find /i "inframind-agent.exe" ^>nul
    echo if %%errorlevel%% equ 0 ^(
    echo     echo  ╔══════════════════════════════════════════════════════════╗
    echo     echo  ║  [SUCESSO] InfraMind Agent instalado e em execucao^^!     ║
    echo     echo  ║  A maquina sera registrada automaticamente no servidor.  ║
    echo     echo  ╚══════════════════════════════════════════════════════════╝
    echo ^) else ^(
    echo     echo  [AVISO] O agente foi instalado mas nao iniciou automaticamente.
    echo     echo  Inicie manualmente: %%INSTALL_DIR%%\inframind-agent.exe
    echo ^)
    echo.
    echo echo  Pressione qualquer tecla para fechar...
    echo pause ^>nul
) > "%OUT_DIR%\instalar.bat"

:: Gera o script de remoção (desinstalador)
echo  [*] Gerando desinstalador...
(
    echo @echo off
    echo net session ^>nul 2^>^&1
    echo if %%errorlevel%% neq 0 ^(
    echo     echo Execute como Administrador^^! & pause & exit /b 1
    echo ^)
    echo echo Removendo InfraMind Agent...
    echo taskkill /f /im inframind-agent.exe ^>nul 2^>^&1
    echo schtasks /delete /tn "InfraMindAgent" /f ^>nul 2^>^&1
    echo timeout /t 2 /nobreak ^>nul
    echo rmdir /s /q "%INSTALL_PATH%" ^>nul 2^>^&1
    echo echo [OK] InfraMind Agent removido com sucesso^^!
    echo pause
) > "%OUT_DIR%\desinstalar.bat"

:: Gera README do pacote
(
    echo # InfraMind Agent — Pacote de Instalação
    echo Empresa  : %COMPANY_NAME%
    echo Servidor : %BACKEND_URL%
    echo Gerado em: %DATE% %TIME%
    echo.
    echo ## Como instalar
    echo 1. Copie esta pasta para a maquina do cliente
    echo 2. Execute `instalar.bat` como Administrador
    echo 3. O agente sera instalado em: %INSTALL_PATH%
    echo 4. Inicio automatico configurado via Agendador de Tarefas
    echo.
    echo ## Remocao
    echo Execute `desinstalar.bat` como Administrador
    echo.
    echo ## Arquivos
    echo - inframind-agent.exe  : Agente de monitoramento
    echo - config.json          : Configuracao pre-definida com token da empresa
    echo - instalar.bat         : Instalador automatico
    echo - desinstalar.bat      : Desinstalador
) > "%OUT_DIR%\LEIA-ME.txt"

:: ── Resultado ────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║              PACOTE GERADO COM SUCESSO!                  ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Localização: %OUT_DIR%
echo.
echo  Conteúdo do pacote:
dir /b "%OUT_DIR%"
echo.
echo  ─────────────────────────────────────────────────────────
echo  PRÓXIMOS PASSOS:
echo    1. Copie a pasta "%OUT_DIR%"
echo       para a máquina do cliente (pen drive, rede, etc.)
echo    2. Na máquina cliente, execute "instalar.bat"
echo       como Administrador
echo    3. Confirme no painel InfraMind que a máquina apareceu
echo  ─────────────────────────────────────────────────────────
echo.

:: Abre a pasta gerada no Explorer
explorer "%OUT_DIR%"

pause
endlocal
