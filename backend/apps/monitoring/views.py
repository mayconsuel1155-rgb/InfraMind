import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.agents.models import Machine
from apps.alerts.models import Alert
from apps.monitoring.models import Metric

def get_company_scope(user):
    """Helper to return querysets filtered by company tenancy (unless superadmin)."""
    if user.role == 'superadmin':
        return Machine.objects.all(), Alert.objects.all()
    
    # If standard user has no company, return empty querysets
    if not user.company:
        return Machine.objects.none(), Alert.objects.none()
        
    machines = Machine.objects.filter(company=user.company)
    alerts = Alert.objects.filter(machine__company=user.company)
    return machines, alerts

@login_required
def dashboard_view(request):
    machines_qs, alerts_qs = get_company_scope(request.user)
    
    # Tickets scope
    from apps.tickets.models import Ticket
    if request.user.role == 'superadmin':
        tickets_qs = Ticket.objects.all()
    else:
        tickets_qs = Ticket.objects.filter(company=request.user.company)
        
    total_machines = machines_qs.count()
    online_count = machines_qs.exclude(status='offline').count()
    offline_count = machines_qs.filter(status='offline').count()
    
    active_critical_alerts = alerts_qs.filter(is_resolved=False, severity='critical')
    active_warnings = alerts_qs.filter(is_resolved=False, severity__in=['high', 'low'])
    
    recent_alerts = alerts_qs.order_by('-created_at')[:10]
    
    active_tickets = tickets_qs.filter(status__in=['open', 'in_progress'])
    
    context = {
        'total_machines': total_machines,
        'online_count': online_count,
        'offline_count': offline_count,
        'critical_count': active_critical_alerts.count(),
        'warning_count': active_warnings.count(),
        'recent_alerts': recent_alerts,
        'active_critical': active_critical_alerts,
        'open_tickets_count': active_tickets.count(),
        'active_tickets': active_tickets[:10],
    }
    return render(request, 'dashboard.html', context)

@login_required
def machine_list_view(request):
    machines_qs, _ = get_company_scope(request.user)
    machines = machines_qs.order_by('hostname')
    return render(request, 'machines/list.html', {'machines': machines})

@login_required
def machine_detail_view(request, pk):
    machines_qs, alerts_qs = get_company_scope(request.user)
    machine = get_object_or_404(machines_qs, pk=pk)
    
    # Fetch recent metrics (last 30) for Chart.js
    metrics = Metric.objects.filter(machine=machine).order_by('-collected_at')[:30]
    metrics = list(reversed(metrics)) # chronologic order for chart
    
    # Format data for Chart.js
    chart_data = {
        'labels': [m.collected_at.strftime('%H:%M') for m in metrics],
        'cpu': [round(m.cpu_percent, 1) for m in metrics],
        'ram': [round(m.ram_percent, 1) for m in metrics],
        'disk': [round(m.disk_percent, 1) for m in metrics],
    }
    
    machine_alerts = alerts_qs.filter(machine=machine).order_by('-created_at')[:10]
    
    from apps.tickets.models import Ticket
    machine_tickets = Ticket.objects.filter(alert__machine=machine).order_by('-created_at')[:10]
    
    # Fetch softwares and security status
    softwares = machine.softwares.all().order_by('name')
    security_status = getattr(machine, 'security_status', None)
    
    context = {
        'machine': machine,
        'alerts': machine_alerts,
        'tickets': machine_tickets,
        'softwares': softwares,
        'security_status': security_status,
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'machines/detail.html', context)

@login_required
def alerts_list_view(request):
    _, alerts_qs = get_company_scope(request.user)
    
    # Filters
    severity = request.GET.get('severity')
    status_filter = request.GET.get('status')
    
    alerts = alerts_qs
    if severity in ['low', 'high', 'critical']:
        alerts = alerts.filter(severity=severity)
    
    if status_filter == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    elif status_filter == 'active':
        alerts = alerts.filter(is_resolved=False)
        
    alerts = alerts.order_by('-created_at')[:50]
    
    return render(request, 'alerts/list.html', {
        'alerts': alerts,
        'severity_filter': severity,
        'status_filter': status_filter
    })

@login_required
def resolve_alert_view(request, pk):
    _, alerts_qs = get_company_scope(request.user)
    alert = get_object_or_404(alerts_qs, pk=pk)
    
    # Only technician, admin or superadmin can resolve alerts
    if request.user.role == 'viewer':
        return HttpResponseForbidden("Você não tem permissão para resolver alertas.")
        
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.save()
    
    # Trigger rules engine to check if machine status should be updated
    from apps.alerts.services import RulesEngineService
    RulesEngineService._update_machine_status(alert.machine)
    
    # Redirect back to where user came from
    next_url = request.GET.get('next', 'alerts_list')
    return redirect(next_url)

@login_required
@require_POST
def machine_delete_view(request, pk):
    if request.user.role not in ['admin', 'superadmin']:
        return HttpResponseForbidden("Você não tem permissão para excluir/descartar máquinas.")
    
    machines_qs, _ = get_company_scope(request.user)
    machine = get_object_or_404(machines_qs, pk=pk)
    hostname = machine.hostname
    
    machine.delete()
    messages.success(request, f"A máquina '{hostname}' foi excluída e descartada com sucesso.")
    return redirect('machine_list')
