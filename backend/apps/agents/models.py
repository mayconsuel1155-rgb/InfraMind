import uuid
from django.db import models
from apps.companies.models import Company
from core.managers import TenantManager

class Machine(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('warning', 'Alerta Médio'),
        ('critical', 'Crítico'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='machines')
    hostname = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    operating_system = models.CharField(max_length=200)
    cpu_model = models.CharField(max_length=200)
    cpu_cores = models.IntegerField()
    ram_total_gb = models.FloatField()
    disk_total_gb = models.FloatField()
    api_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(choices=STATUS_CHOICES, max_length=20, default='offline')
    last_seen = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    ram_details = models.TextField(blank=True, default='', verbose_name="Detalhes da Memória")
    disk_details = models.TextField(blank=True, default='', verbose_name="Detalhes do Disco")

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'

    def __str__(self):
        return f"{self.hostname} ({self.company.name})"

    @property
    def is_authenticated(self):
        return True
