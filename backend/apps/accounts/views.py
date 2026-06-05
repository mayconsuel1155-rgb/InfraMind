from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
import json
import uuid

from apps.accounts.models import User, LGPDAuditLog
from apps.tickets.models import Ticket, TicketWorkLog

class EmailAuthenticationForm(forms.Form):
    username = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={
        'class': 'form-control form-control-lg bg-dark text-light border-secondary',
        'placeholder': 'exemplo@empresa.com'
    }))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={
        'class': 'form-control form-control-lg bg-dark text-light border-secondary',
        'placeholder': 'Sua senha'
    }))

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_message = None
    if request.method == 'POST':
        form = EmailAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    error_message = "Esta conta de usuário foi desativada."
            else:
                error_message = "E-mail ou senha incorretos."
    else:
        form = EmailAuthenticationForm()

    return render(request, 'login.html', {'form': form, 'error_message': error_message})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def lgpd_consent_view(request):
    if request.user.lgpd_accepted_terms:
        return redirect('dashboard')
    
    if request.method == 'POST':
        user = request.user
        user.lgpd_accepted_terms = True
        user.lgpd_accepted_at = timezone.now()
        user.lgpd_terms_version = "1.0"
        user.save()
        
        # Log audit entry
        client_ip = request.META.get('REMOTE_ADDR')
        LGPDAuditLog.objects.create(
            operator=user,
            company=user.company,
            target_email=user.email,
            action='consent_accept',
            details=f"O usuário aceitou os Termos de Uso e Política de Privacidade na versão {user.lgpd_terms_version}.",
            ip_address=client_ip
        )
        return redirect('dashboard')
        
    return render(request, 'lgpd_consent.html')


@login_required
def lgpd_export_data_view(request, user_id=None):
    current_user = request.user
    
    if user_id:
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponseForbidden("Usuário não encontrado.")
            
        if current_user.role != 'superadmin':
            if current_user.role != 'admin' or target_user.company != current_user.company:
                return HttpResponseForbidden("Sem permissão para exportar os dados deste usuário.")
    else:
        target_user = current_user
        
    # Gather data
    data = {
        "user_profile": {
            "email": target_user.email,
            "role": target_user.get_role_display(),
            "company": target_user.company.name if target_user.company else None,
            "is_active": target_user.is_active,
            "created_at": target_user.created_at.isoformat() if target_user.created_at else None,
            "updated_at": target_user.updated_at.isoformat() if target_user.updated_at else None,
        },
        "lgpd_consent": {
            "accepted_terms": target_user.lgpd_accepted_terms,
            "accepted_at": target_user.lgpd_accepted_at.isoformat() if target_user.lgpd_accepted_at else None,
            "terms_version": target_user.lgpd_terms_version,
        },
        "tickets_assigned": list(Ticket.objects.filter(assigned_to=target_user).values(
            'id', 'title', 'status', 'priority', 'created_at', 'resolved_at'
        )),
        "work_logs": list(TicketWorkLog.objects.filter(user=target_user).values(
            'id', 'ticket_id', 'note', 'started_at', 'duration_seconds'
        )),
        "audit_logs": list(LGPDAuditLog.objects.filter(target_email=target_user.email).values(
            'action', 'details', 'ip_address', 'created_at'
        ))
    }
    
    # Log audit entry
    client_ip = request.META.get('REMOTE_ADDR')
    LGPDAuditLog.objects.create(
        operator=current_user,
        company=current_user.company,
        target_email=target_user.email,
        action='data_export',
        details=f"Dados pessoais exportados por solicitação do titular (operador: {current_user.email}).",
        ip_address=client_ip
    )
    
    response = HttpResponse(json.dumps(data, indent=4, default=str), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="portabilidade_{target_user.email}.json"'
    return response


@login_required
def lgpd_anonymize_user_view(request, user_id):
    current_user = request.user
    
    if current_user.role not in ('admin', 'superadmin'):
        return HttpResponseForbidden("Apenas administradores podem anonimizar contas de usuários.")
        
    target_user = get_object_or_404(User, id=user_id)
    
    if current_user.role == 'admin' and target_user.company != current_user.company:
        return HttpResponseForbidden("Você só pode anonimizar usuários da sua própria empresa.")
        
    if target_user.role == 'superadmin' and current_user.role != 'superadmin':
        return HttpResponseForbidden("Não é permitido anonimizar contas de Super Administradores.")
        
    if target_user == current_user:
        return HttpResponseForbidden("Não é permitido anonimizar a si mesmo a partir do painel.")
        
    original_email = target_user.email
    
    # Anonymization
    unique_suffix = uuid.uuid4().hex[:8]
    target_user.email = f"anonimo_{unique_suffix}@inframind.local"
    target_user.is_active = False
    target_user.set_unusable_password()
    target_user.save()
    
    # Log audit entry
    client_ip = request.META.get('REMOTE_ADDR')
    LGPDAuditLog.objects.create(
        operator=current_user,
        company=current_user.company,
        target_email=original_email,
        action='anonymization',
        details=f"O usuário foi anonimizado por solicitação do titular. Identificadores apagados. Novo email fictício: {target_user.email}. Conta desativada.",
        ip_address=client_ip
    )
    
    messages.success(request, f"O usuário '{original_email}' foi anonimizado com sucesso e sua conta foi inativada.")
    return redirect('management_console')


@login_required
def user_reset_password_view(request, user_id):
    current_user = request.user
    
    if current_user.role not in ('admin', 'superadmin'):
        return HttpResponseForbidden("Sem permissão para alterar senhas.")
        
    target_user = get_object_or_404(User, id=user_id)
    
    # Tenancy check
    if current_user.role == 'admin' and target_user.company != current_user.company:
        return HttpResponseForbidden("Sem permissão para alterar senhas de outra empresa.")
        
    # Superadmin check
    if target_user.role == 'superadmin' and current_user.role != 'superadmin':
        return HttpResponseForbidden("Não é permitido alterar a senha de um Super Administrador.")
        
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        if not new_password:
            messages.error(request, "A nova senha não pode ser vazia.")
            return redirect('management_console')
            
        from django.core.exceptions import ValidationError
        from django.contrib.auth.password_validation import validate_password
        
        try:
            validate_password(new_password, target_user)
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
            return redirect('management_console')
            
        target_user.set_password(new_password)
        target_user.save()
        
        # Log in audit
        client_ip = request.META.get('REMOTE_ADDR')
        LGPDAuditLog.objects.create(
            operator=current_user,
            company=current_user.company,
            target_email=target_user.email,
            action='user_update',
            details=f"Senha de acesso reiniciada pelo operador {current_user.email}.",
            ip_address=client_ip
        )
        
        messages.success(request, f"Senha do usuário {target_user.email} alterada com sucesso.")
        
    return redirect('management_console')
