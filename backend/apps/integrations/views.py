import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.alerts.models import Alert
from apps.companies.models import Company
from apps.integrations.models import AIConfig
from apps.integrations.services import AIService
from apps.monitoring.models import Metric

MASK = "••••••••"


def _resolve_company(user):
    if getattr(user, "company", None):
        return user.company
    if user.role == 'superadmin':
        return Company.objects.filter(is_active=True).first()
    return None


def _mask_api_key(raw_key: str) -> str:
    if not raw_key:
        return ""
    if len(raw_key) <= 8:
        return MASK
    return f"{raw_key[:4]}{MASK}{raw_key[-4:]}"


@login_required
def ai_config_view(request):
    if request.user.role not in ['admin', 'superadmin']:
        return HttpResponseForbidden("Apenas administradores podem gerenciar configurações de IA.")

    company = _resolve_company(request.user)
    if not company:
        return HttpResponseForbidden("Sua conta não está associada a nenhuma empresa ativa.")

    ai_config, _ = AIConfig.objects.get_or_create(
        company=company,
        defaults={"api_key_encrypted": ""},
    )

    success_message = None
    error_message = None

    if request.method == 'POST':
        provider = (request.POST.get('provider') or '').strip()
        model_name = (request.POST.get('model_name') or '').strip()
        if model_name == 'custom':
            model_name = (request.POST.get('model_name_custom') or '').strip()
        api_key = (request.POST.get('api_key') or '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if provider and model_name:
            ai_config.provider = provider
            ai_config.model_name = model_name
            if api_key and MASK not in api_key:
                ai_config.api_key = api_key
            ai_config.is_active = is_active
            ai_config.save()
            success_message = "Configurações de IA salvas com sucesso."
        else:
            error_message = "Todos os campos obrigatórios devem ser preenchidos."

    context = {
        'ai_config': ai_config,
        'masked_api_key': _mask_api_key(ai_config.api_key),
        'success_message': success_message,
        'error_message': error_message,
    }
    return render(request, 'integrations/ai_config.html', context)


@login_required
@require_POST
def api_test_ai(request):
    if request.user.role not in ['admin', 'superadmin']:
        return JsonResponse({"status": "error", "message": "Sem permissão"}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)

    provider = (data.get('provider') or '').strip()
    model_name = (data.get('model_name') or '').strip()
    api_key = (data.get('api_key') or '').strip()

    if not provider or not model_name:
        return JsonResponse({"status": "error", "message": "Provedor e modelo são obrigatórios."}, status=400)

    if not api_key or MASK in api_key:
        company = _resolve_company(request.user)
        if not company:
            return JsonResponse({"status": "error", "message": "Nenhuma empresa ativa foi encontrada para usar a chave salva."}, status=400)

        try:
            ai_config = AIConfig.objects.get(company=company)
        except AIConfig.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Por favor, digite uma chave de API para testar."}, status=400)

        api_key = ai_config.api_key

    if not api_key:
        return JsonResponse({"status": "error", "message": "Chave de API em branco."}, status=400)

    success, message = AIService.test_connection(provider, model_name, api_key)
    if success:
        return JsonResponse({"status": "ok", "message": message})
    return JsonResponse({"status": "error", "message": message})


@login_required
def alert_ai_diagnosis_view(request, pk):
    try:
        if request.user.role == 'superadmin':
            alert = Alert.objects.get(pk=pk)
        else:
            alert = Alert.objects.get(pk=pk, machine__company=request.user.company)
    except Alert.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Alerta não encontrado ou sem permissão."}, status=404)

    machine = alert.machine

    ai_service = AIService(machine.company)
    if not ai_service.is_configured():
        return JsonResponse({
            "status": "not_configured",
            "message": "A integração de IA não está configurada para esta empresa. Um administrador deve configurá-la em Configurações de IA.",
        })

    recent_metrics = Metric.objects.filter(machine=machine).order_by('-collected_at')[:10]
    recent_metrics = list(reversed(recent_metrics))
    metrics_str = "\n".join([
        f"- {m.collected_at.strftime('%H:%M:%S')}: CPU={m.cpu_percent}%, RAM={m.ram_percent}%, Disco={m.disk_percent}%"
        for m in recent_metrics
    ])

    prompt = f"""Você é o Engenheiro de Suporte e Diagnóstico por IA do InfraMind.
Analise o incidente de infraestrutura e forneça um relatório técnico detalhado e acionável.

Especificações da Máquina:
- Hostname: {machine.hostname}
- Sistema Operacional: {machine.operating_system}
- CPU: {machine.cpu_model} ({machine.cpu_cores} núcleos)
- RAM Total: {machine.ram_total_gb} GB
- Disco Total: {machine.disk_total_gb} GB

Detalhes do Alerta:
- Tipo de Alerta: {alert.type}
- Severidade: {alert.severity}
- Mensagem: {alert.message}
- Registrado em: {alert.created_at.strftime('%d/%m/%Y %H:%M:%S')}

Histórico Recente de Métricas:
{metrics_str if metrics_str else 'Nenhuma métrica registrada.'}

Por favor, elabore sua resposta estruturada em Markdown contendo exatamente as seguintes seções numeradas (sem emojis):

## 1. INTRODUÇÃO E ANÁLISE DO INCIDENTE
(Resuma o que está acontecendo e a criticidade do status atual da máquina, de forma impessoal e formal)

## 2. POSSÍVEIS CAUSAS ANALISADAS
(Cite 2 ou 3 causas mais prováveis baseadas no consumo observado e no SO da máquina)

## 3. PLANO DE AÇÃO E COMANDOS RECOMENDADOS
(Forneça comandos práticos e específicos para o sistema operacional {machine.operating_system} para diagnosticar e sanar a causa raiz)
"""

    diagnosis = ai_service.generate_completion(prompt)

    return JsonResponse({
        "status": "ok",
        "diagnosis": diagnosis,
        "severity": alert.severity,
    })
