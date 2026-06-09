import io
import json
import zipfile

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.contrib.auth.decorators import login_required

from apps.companies.models import Company


def _is_admin(user):
    return user.role in ('admin', 'superadmin')


def _get_backend_url(request):
    """
    Retorna a URL pública do backend configurada no .env (AGENT_PUBLIC_URL).
    Se não configurada, usa a URL da própria requisição como fallback.
    """
    configured = getattr(settings, 'AGENT_PUBLIC_URL', '').strip()
    if configured:
        return configured.rstrip('/')
    scheme = 'https' if request.is_secure() else 'http'
    return f"{scheme}://{request.get_host()}"


def _build_instalar_bat(company_name, backend_url, install_path=r"C:\Program Files\InfraMind"):
    """Gera o conteúdo do instalar.bat dinamicamente para a empresa."""
    lines = [
        "@echo off",
        "setlocal EnableDelayedExpansion",
        "chcp 65001 >nul 2>&1",
        "",
        ":: Verifica privilégios de administrador",
        "net session >nul 2>&1",
        "if %errorlevel% neq 0 (",
        "    echo [ERRO] Execute este instalador como Administrador!",
        r"    echo Clique com botao direito em instalar.bat e escolha ""Executar como administrador""",
        "    pause",
        "    exit /b 1",
        ")",
        "",
        "color 0B",
        "cls",
        "echo.",
        "echo  ╔══════════════════════════════════════════════════════════╗",
        "echo  ║         InfraMind Agent — Instalador Automatico          ║",
        f"echo  ║  Empresa : {company_name:<46}║",
        f"echo  ║  Servidor: {backend_url:<46}║",
        "echo  ╚══════════════════════════════════════════════════════════╝",
        "echo.",
        "echo  [*] Instalando agente de monitoramento InfraMind...",
        "echo.",
        "",
        f'set "INSTALL_DIR={install_path}"',
        "echo  [*] Criando pasta de instalacao: %INSTALL_DIR%",
        'if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"',
        "",
        ":: Encerra processo existente do agente (se houver)",
        "echo  [*] Verificando processos existentes...",
        "taskkill /f /im inframind-agent.exe >nul 2>&1",
        "timeout /t 2 /nobreak >nul",
        "",
        ":: Copia os arquivos",
        "echo  [*] Copiando arquivos do agente...",
        'copy /y "%~dp0inframind-agent.exe" "%INSTALL_DIR%\\inframind-agent.exe" >nul',
        'copy /y "%~dp0config.json" "%INSTALL_DIR%\\config.json" >nul',
        "",
        ":: Remove tarefa agendada anterior (se existir)",
        "echo  [*] Configurando inicializacao automatica com o Windows...",
        'schtasks /delete /tn "InfraMindAgent" /f >nul 2>&1',
        "",
        ":: Cria tarefa agendada para iniciar com o Windows (conta SYSTEM)",
        'schtasks /create /tn "InfraMindAgent" /tr "\\"%INSTALL_DIR%\\inframind-agent.exe\\"" /sc onstart /ru "SYSTEM" /rl highest /f >nul',
        "",
        "if %errorlevel% equ 0 (",
        "    echo  [OK] Tarefa agendada criada com sucesso!",
        ") else (",
        "    echo  [AVISO] Falha ao criar tarefa agendada. Configure manualmente se necessario.",
        ")",
        "",
        ":: Inicia o agente imediatamente",
        "echo  [*] Iniciando agente de monitoramento...",
        'start "" "%INSTALL_DIR%\\inframind-agent.exe"',
        "timeout /t 3 /nobreak >nul",
        "",
        ":: Verifica se o processo está rodando",
        'tasklist /fi "imagename eq inframind-agent.exe" 2>nul | find /i "inframind-agent.exe" >nul',
        "if %errorlevel% equ 0 (",
        "    echo.",
        "    echo  ╔══════════════════════════════════════════════════════════╗",
        "    echo  ║  [SUCESSO] InfraMind Agent instalado e em execucao!      ║",
        "    echo  ║  A maquina sera registrada automaticamente no servidor.  ║",
        "    echo  ╚══════════════════════════════════════════════════════════╝",
        ") else (",
        "    echo  [AVISO] O agente foi instalado mas nao iniciou automaticamente.",
        "    echo  Inicie manualmente: %INSTALL_DIR%\\inframind-agent.exe",
        ")",
        "",
        "echo.",
        "echo  Pressione qualquer tecla para fechar...",
        "pause >nul",
    ]
    return "\r\n".join(lines)


def _build_desinstalar_bat(install_path=r"C:\Program Files\InfraMind"):
    """Gera o conteúdo do desinstalar.bat."""
    lines = [
        "@echo off",
        "net session >nul 2>&1",
        "if %errorlevel% neq 0 (",
        "    echo Execute como Administrador!",
        "    pause & exit /b 1",
        ")",
        "echo Removendo InfraMind Agent...",
        "taskkill /f /im inframind-agent.exe >nul 2>&1",
        'schtasks /delete /tn "InfraMindAgent" /f >nul 2>&1',
        "timeout /t 2 /nobreak >nul",
        f'rmdir /s /q "{install_path}" >nul 2>&1',
        "echo [OK] InfraMind Agent removido com sucesso!",
        "pause",
    ]
    return "\r\n".join(lines)


@login_required
def download_agent_installer(request, company_id):
    """
    Gera e serve um arquivo ZIP com o instalador do agente pré-configurado
    para a empresa especificada. Inspirado no fluxo do Milvus.
    """
    if not _is_admin(request.user):
        return HttpResponseForbidden("Apenas administradores podem baixar instaladores.")

    # Carrega a empresa respeitando o escopo do tenant
    try:
        if request.user.role == 'superadmin':
            company = Company.objects_all.get(pk=company_id)
        else:
            # Admin só pode baixar para sua empresa ou filiais
            company = Company.objects.get(pk=company_id)
            if company.pk != request.user.company_id and company.parent_company_id != request.user.company_id:
                return HttpResponseForbidden("Sem permissão para baixar instalador desta empresa.")
    except Company.DoesNotExist:
        return HttpResponseNotFound("Empresa não encontrada.")

    # Verifica se o executável do agente está disponível
    exe_path = settings.AGENT_EXE_PATH
    if not exe_path.exists():
        return HttpResponseNotFound(
            "Executável do agente não encontrado no servidor. "
            "Copie 'inframind-agent.exe' para 'backend/static/agent/' após o build."
        )

    backend_url = _get_backend_url(request)

    # Monta o config.json pré-configurado
    config_data = {
        "backend_url": backend_url,
        "registration_token": company.registration_token,
    }
    config_json = json.dumps(config_data, indent=4, ensure_ascii=False)

    # Gera os scripts .bat dinamicamente
    instalar_bat = _build_instalar_bat(
        company_name=company.name,
        backend_url=backend_url,
    )
    desinstalar_bat = _build_desinstalar_bat()

    # Leia-me do pacote
    readme = (
        f"# InfraMind Agent — Pacote de Instalação\n"
        f"Empresa  : {company.name}\n"
        f"Servidor : {backend_url}\n"
        f"Token    : {company.registration_token}\n\n"
        f"## Como instalar\n"
        f"1. Execute 'instalar.bat' como Administrador\n"
        f"2. O agente será instalado em: C:\\Program Files\\InfraMind\\\n"
        f"3. Início automático configurado via Agendador de Tarefas (SYSTEM)\n"
        f"4. A máquina aparecerá no painel InfraMind em até 60 segundos\n\n"
        f"## Remoção\n"
        f"Execute 'desinstalar.bat' como Administrador\n"
    )

    # Empacota tudo num ZIP em memória (sem gravar em disco)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Executável do agente
        with open(exe_path, 'rb') as exe_file:
            zf.writestr('inframind-agent.exe', exe_file.read())
        # config.json pré-configurado
        zf.writestr('config.json', config_json.encode('utf-8'))
        # Scripts de instalação/remoção
        zf.writestr('instalar.bat', instalar_bat.encode('cp1252', errors='replace'))
        zf.writestr('desinstalar.bat', desinstalar_bat.encode('cp1252', errors='replace'))
        # Leia-me
        zf.writestr('LEIA-ME.txt', readme.encode('utf-8'))

    zip_buffer.seek(0)

    # Nome do arquivo de download
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in company.name)
    filename = f"InfraMind_{safe_name}_installer.zip"

    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
