from apps.agents.models import Machine
from apps.alerts.models import Alert

def inframind_stats(request):
    if not request.user.is_authenticated:
        return {}

    # Define scope
    user = request.user
    if user.role == 'superadmin':
        machines_qs = Machine.objects.all()
        alerts_qs = Alert.objects.all()
        # Find some registration token to display
        from apps.companies.models import Company
        first_company = Company.objects.first()
        global_token = first_company.registration_token if first_company else "Nenhum token gerado"
        company_name = "Super Admin (Verificando todas)"
    else:
        company = user.company
        if company:
            machines_qs = Machine.objects.filter(company=company)
            alerts_qs = Alert.objects.filter(machine__company=company)
            global_token = company.registration_token
            company_name = company.name
        else:
            machines_qs = Machine.objects.none()
            alerts_qs = Alert.objects.none()
            global_token = "Sem empresa"
            company_name = "Sem empresa"

    total_machines = machines_qs.count()
    online_count = machines_qs.exclude(status='offline').count()
    offline_count = machines_qs.filter(status='offline').count()
    active_alerts_count = alerts_qs.filter(is_resolved=False).count()

    return {
        'global_company_name': company_name,
        'global_registration_token': global_token,
        'global_total_machines': total_machines,
        'global_online_count': online_count,
        'global_offline_count': offline_count,
        'global_active_alerts_count': active_alerts_count,
    }
