from django.db import models
from apps.accounts.models import User
from apps.companies.models import Company

class GlobalAuditLog(models.Model):
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs', verbose_name="Operador")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs', verbose_name="Tenant")
    action = models.CharField(max_length=100, verbose_name="Ação Executada")
    path = models.CharField(max_length=500, verbose_name="Caminho / URL", null=True, blank=True)
    method = models.CharField(max_length=10, verbose_name="Método HTTP", null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Endereço IP")
    user_agent = models.TextField(null=True, blank=True, verbose_name="User Agent")
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes da Requisição (Body/Params)")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Data/Hora")

    class Meta:
        verbose_name = "Log de Auditoria Global"
        verbose_name_plural = "Logs de Auditoria Globais"
        ordering = ['-created_at']

    def __str__(self):
        op = self.operator.email if self.operator else "Sistema/Anônimo"
        return f"[{self.created_at}] {op} - {self.action} na URL {self.path}"
