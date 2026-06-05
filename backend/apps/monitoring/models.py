from django.db import models
from apps.agents.models import Machine

from core.managers import TenantManager

class Metric(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='metrics')
    cpu_percent = models.FloatField()
    ram_percent = models.FloatField()
    disk_percent = models.FloatField()
    collected_at = models.DateTimeField()

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = 'Métrica'
        verbose_name_plural = 'Métricas'
        ordering = ['-collected_at']

    def __str__(self):
        return f"{self.machine.hostname} - CPU: {self.cpu_percent}%, RAM: {self.ram_percent}% em {self.collected_at}"
