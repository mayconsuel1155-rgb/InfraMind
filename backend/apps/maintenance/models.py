from django.db import models
from apps.companies.models import Company
from apps.agents.models import Machine
from apps.tickets.models import Ticket
from django.contrib.auth import get_user_model
from core.managers import TenantManager

User = get_user_model()

class MaintenanceReport(models.Model):
    TYPE_CHOICES = [
        ('corrective',    'Corretiva'),       
        ('preventive',    'Preventiva'),      
        ('upgrade_hw',    'Upgrade Hardware'),
        ('upgrade_sw',    'Upgrade Software'),
        ('cleaning',      'Limpeza'),         
        ('other',         'Outro'),
    ]
    STATUS_CHOICES = [
        ('planned',       'Planejada'),
        ('in_progress',   'Em Andamento'),
        ('completed',     'Concluída'),
        ('cancelled',     'Cancelada'),
    ]

    company       = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='maintenance_reports')
    machine       = models.ForeignKey(Machine, null=True, blank=True, on_delete=models.SET_NULL, related_name='maintenances')
    ticket        = models.ForeignKey(Ticket, null=True, blank=True, on_delete=models.SET_NULL, related_name='maintenances')
    technician    = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='performed_maintenances')
    type          = models.CharField(choices=TYPE_CHOICES, max_length=20, default='corrective')
    status        = models.CharField(choices=STATUS_CHOICES, max_length=20, default='planned')
    title         = models.CharField(max_length=300)
    description   = models.TextField()
    work_done     = models.TextField(blank=True)
    scheduled_at  = models.DateTimeField(null=True, blank=True)
    started_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)
    cost          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.00)
    warranty_days = models.IntegerField(default=0)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = 'Relatório de Manutenção'
        verbose_name_plural = 'Relatórios de Manutenção'
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.id} - {self.title} ({self.get_status_display()})"
    
    @property
    def total_cost(self):
        items_cost = sum([item.total_cost for item in self.items.all()])
        base_cost = self.cost or 0
        return base_cost + items_cost

class MaintenanceItem(models.Model):
    report      = models.ForeignKey(MaintenanceReport, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity    = models.PositiveIntegerField(default=1)
    unit_cost   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.00)

    class Meta:
        verbose_name = 'Item de Manutenção'
        verbose_name_plural = 'Itens de Manutenção'

    def __str__(self):
        return f"{self.quantity}x {self.description}"

    @property
    def total_cost(self):
        return self.quantity * (self.unit_cost or 0)
