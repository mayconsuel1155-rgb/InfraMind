from django.db import models
from apps.agents.models import Machine
from apps.companies.models import Company

class MonitoringThreshold(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='monitoring_threshold')
    cpu_limit = models.FloatField(default=95.0, verbose_name="Limite de CPU (%)")
    ram_limit = models.FloatField(default=90.0, verbose_name="Limite de RAM (%)")
    disk_limit = models.FloatField(default=80.0, verbose_name="Limite de Disco (%)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Limites de Monitoramento"
        verbose_name_plural = "Limites de Monitoramento"

    def __str__(self):
        return f"Limites - {self.company.name} (CPU: {self.cpu_limit}%, RAM: {self.ram_limit}%, Disco: {self.disk_limit}%)"

from core.managers import TenantManager

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Baixo'),
        ('high', 'Alto'),
        ('critical', 'Crítico'),
    ]

    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(choices=SEVERITY_CHOICES, max_length=20)
    type = models.CharField(max_length=100)  # e.g., 'cpu_high', 'ram_high', 'disk_warning', 'machine_offline'
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-created_at']

    def __str__(self):
        status_str = "Resolvido" if self.is_resolved else "Ativo"
        return f"[{self.severity.upper()}] {self.machine.hostname} - {self.type} ({status_str})"
