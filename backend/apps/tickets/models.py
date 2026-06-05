from django.db import models
from apps.companies.models import Company
from apps.alerts.models import Alert
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.managers import TenantManager

User = get_user_model()

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Aberto'),
        ('in_progress', 'Em Andamento'),
        ('resolved', 'Resolvido'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='tickets')
    alert = models.ForeignKey(Alert, null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets')
    machine = models.ForeignKey('agents.Machine', null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets')
    title = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(choices=STATUS_CHOICES, max_length=20, default='open')
    priority = models.CharField(choices=PRIORITY_CHOICES, max_length=20, default='medium')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    ai_report = models.TextField(blank=True)
    ai_report_generated_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = 'Chamado'
        verbose_name_plural = 'Chamados'
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.id} - {self.title} ({self.get_status_display()})"

    @property
    def total_work_seconds(self):
        total = 0
        for log in self.work_logs.all():
            total += log.duration_seconds if log.duration_seconds else 0
            if log.is_active:
                total += int((timezone.now() - log.started_at).total_seconds())
        return total


class TicketWorkLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='work_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_work_logs')
    note = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = 'Apontamento de Chamado'
        verbose_name_plural = 'Apontamentos de Chamado'
        ordering = ['-started_at']

    def __str__(self):
        state = "Em andamento" if self.is_active else "Pausado"
        return f"{self.ticket_id} - {self.user.email} ({state})"

    def pause(self):
        if not self.is_active:
            return

        self.paused_at = timezone.now()
        self.duration_seconds = max(0, int((self.paused_at - self.started_at).total_seconds()))
        self.is_active = False
        self.save(update_fields=['paused_at', 'duration_seconds', 'is_active'])

    @property
    def effective_duration_seconds(self):
        if self.is_active:
            return self.duration_seconds + int((timezone.now() - self.started_at).total_seconds())
        return self.duration_seconds

    @property
    def display_duration(self):
        total_seconds = max(0, int(self.effective_duration_seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
