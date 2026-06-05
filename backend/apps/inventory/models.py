from django.db import models
from apps.agents.models import Machine

from core.managers import TenantManager

class InstalledSoftware(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='softwares')
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=100, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    installed_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        unique_together = ('machine', 'name')
        verbose_name = "Software Instalado"
        verbose_name_plural = "Softwares Instalados"

    def __str__(self):
        return f"{self.name} ({self.version}) em {self.machine.hostname}"


class SecurityStatus(models.Model):
    machine = models.OneToOneField(Machine, on_delete=models.CASCADE, related_name='security_status')
    antivirus_active = models.BooleanField(default=True)
    firewall_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = "Status de Segurança"
        verbose_name_plural = "Status de Segurança"

    def __str__(self):
        return f"Segurança de {self.machine.hostname}: AV={self.antivirus_active}, FW={self.firewall_active}"
