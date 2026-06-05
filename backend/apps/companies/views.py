from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from apps.accounts.models import User, LGPDAuditLog
from apps.companies.forms import CompanyForm, UserForm
from apps.companies.models import Company
from apps.agents.models import Machine
from apps.alerts.models import Alert
from apps.tickets.models import Ticket


def _is_admin(user):
    return user.role in ('admin', 'superadmin')


def _management_scope(user):
    if user.role == 'superadmin':
        return Company.objects_all.all().order_by('-created_at')
    if user.company_id:
        return Company.objects.all().order_by('-created_at')
    return Company.objects.none()


@login_required
def management_console_view(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Apenas administradores podem acessar o console de gestao.')

    can_manage_companies = request.user.role in ('superadmin', 'admin')
    companies = _management_scope(request.user)

    users = User.objects.select_related('company').order_by('company__name', 'email')

    selected_company = request.GET.get('company')
    if selected_company and request.user.role == 'superadmin':
        users = users.filter(company_id=selected_company)

    company_form = CompanyForm(current_user=request.user, prefix='company') if can_manage_companies else None
    user_form = UserForm(current_user=request.user, prefix='user')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_company' and can_manage_companies:
            company_form = CompanyForm(request.POST, request.FILES, current_user=request.user, prefix='company')
            if company_form.is_valid():
                company = company_form.save()
                messages.success(
                    request,
                    f"Empresa '{company.name}' criada com sucesso. Token: {company.registration_token}",
                )
                return redirect('management_console')

        elif action == 'edit_company' and can_manage_companies:
            company_id = request.POST.get('company_id')
            try:
                company_instance = Company.objects_all.get(pk=company_id)
                # Permission check
                if request.user.role != 'superadmin' and company_instance.pk != request.user.company_id and company_instance.parent_company_id != request.user.company_id:
                    return HttpResponseForbidden("Sem permissão para editar esta empresa.")
                
                edit_form = CompanyForm(request.POST, request.FILES, instance=company_instance, current_user=request.user)
                if edit_form.is_valid():
                    edit_form.save()
                    messages.success(request, f"Empresa '{company_instance.name}' atualizada com sucesso.")
                    return redirect('management_console')
                else:
                    messages.error(request, f"Erro ao atualizar empresa: {edit_form.errors.as_text()}")
            except Company.DoesNotExist:
                messages.error(request, "Empresa não encontrada.")

        elif action == 'create_user':
            user_form = UserForm(request.POST, current_user=request.user, prefix='user')
            if user_form.is_valid():
                user = user_form.save()
                
                # Log audit entry
                client_ip = request.META.get('REMOTE_ADDR')
                LGPDAuditLog.objects.create(
                    operator=request.user,
                    company=request.user.company if request.user.role != 'superadmin' else user.company,
                    target_email=user.email,
                    action='user_creation',
                    details=f"Novo usuário criado com perfil '{user.get_role_display()}'.",
                    ip_address=client_ip
                )
                
                messages.success(request, f"Usuario '{user.email}' criado com sucesso.")
                return redirect('management_console')

    company_ids = companies.values_list('id', flat=True)
    machines_qs = Machine.objects.filter(company_id__in=company_ids)
    alerts_qs = Alert.objects.filter(machine__company_id__in=company_ids)
    tickets_qs = Ticket.objects.filter(company_id__in=company_ids)

    # LGPD Audit Logs query based on company scope
    if request.user.role == 'superadmin':
        lgpd_logs = LGPDAuditLog.objects.all().select_related('operator', 'company').order_by('-created_at')[:100]
    else:
        lgpd_logs = LGPDAuditLog.objects.filter(company=request.user.company).select_related('operator', 'company').order_by('-created_at')[:100]

    context = {
        'company_form': company_form,
        'user_form': user_form,
        'companies': companies,
        'users': users,
        'lgpd_logs': lgpd_logs,
        'companies_count': companies.count(),
        'users_count': users.count(),
        'machines_count': machines_qs.count(),
        'alerts_count': alerts_qs.count(),
        'tickets_count': tickets_qs.count(),
        'can_manage_companies': can_manage_companies,
    }
    return render(request, 'management/console.html', context)
