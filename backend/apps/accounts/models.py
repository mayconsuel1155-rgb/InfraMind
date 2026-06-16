from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from apps.companies.models import Company

class UserManager(BaseUserManager):
    def get_queryset(self):
        from core.tenancy import get_current_tenant
        from core.managers import TenantQuerySet
        queryset = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant:
            return queryset.for_tenant(tenant)
        return queryset

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Administrador'),
        ('technician', 'Técnico'),
        ('viewer', 'Visualizador'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    email = models.EmailField(unique=True)
    role = models.CharField(choices=ROLE_CHOICES, max_length=20, default='viewer')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # LGPD Consent Fields
    lgpd_accepted_terms = models.BooleanField(default=False, verbose_name="Aceitou Termos LGPD")
    lgpd_accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Data de Aceite LGPD")
    lgpd_terms_version = models.CharField(max_length=10, default="1.0", verbose_name="Versão dos Termos")

    # MFA Fields
    mfa_secret = models.CharField(max_length=32, blank=True, null=True, verbose_name="Segredo MFA (TOTP)")
    mfa_enabled = models.BooleanField(default=False, verbose_name="MFA Ativado")

    objects = UserManager()
    objects_all = models.Manager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return f"{self.email} ({self.role})"


class LGPDAuditLog(models.Model):
    ACTION_CHOICES = [
        ('consent_accept', 'Aceite dos Termos de Uso/Privacidade'),
        ('data_export', 'Exportação de Dados Pessoais (Portabilidade)'),
        ('anonymization', 'Anonimização de Conta (Exclusão/Esquecimento)'),
        ('role_change', 'Alteração de Nível de Acesso'),
        ('user_creation', 'Criação de Usuário'),
        ('user_update', 'Alteração de Cadastro de Usuário'),
    ]
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lgpd_actions_done', verbose_name="Operador (DPO/Admin)")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='lgpd_logs', verbose_name="Empresa")
    target_email = models.CharField(max_length=255, verbose_name="E-mail do Titular")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name="Operação de Tratamento")
    details = models.TextField(verbose_name="Detalhes da Operação")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Endereço IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        verbose_name = "Log de Auditoria LGPD"
        verbose_name_plural = "Logs de Auditoria LGPD"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.target_email} - {self.get_action_display()} ({self.created_at})"
