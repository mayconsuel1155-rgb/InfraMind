@echo off
title InfraMind - Compilador Universal
cls

echo ============================================================
echo          INFRAMIND - BUILDER STANDALONE E INSTALADORES
echo ============================================================
echo.

:: 1. Compilar o Backend
echo [*] Compilando Servidor Backend (PyInstaller)...
cd backend
call ..\venv\Scripts\activate.bat
pyinstaller --clean inframind-server.spec
if %errorlevel% neq 0 (
    echo [-] Erro ao compilar o backend.
    pause
    exit /b
)
cd ..

:: 2. Compilar o Agent
echo [*] Compilando Agente (PyInstaller)...
cd agent
call ..\venv\Scripts\activate.bat
pyinstaller --clean inframind-agent.spec
if %errorlevel% neq 0 (
    echo [-] Erro ao compilar o agente.
    pause
    exit /b
)
cd ..

:: 3. Gerar Instaladores Inno Setup
echo [*] Gerando Instaladores (Inno Setup)...

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo [+] Inno Setup encontrado. Compilando instalador do servidor...
    %ISCC% build_server.iss
    
    echo [+] Compilando instalador do agente...
    %ISCC% agent\build_agent.iss
    
    echo.
    echo ============================================================
    echo [+] SUCESSO: Instaladores gerados!
    echo ============================================================
    echo - Servidor: dist\InfraMind_Server_Setup.exe
    echo - Agente:   agent\dist\InfraMind_Agent_Setup.exe
) else (
    echo [!] AVISO: Inno Setup 6 (ISCC.exe) não encontrado em C:\Program Files (x86)\Inno Setup 6.
    echo [+] Os binarios standalone (.exe) foram criados nas pastas "dist",
    echo     porem os instaladores (Setup.exe) nao foram gerados.
    echo     Baixe e instale o Inno Setup para gerar os instaladores finais.
)

echo.
pause
