from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from apps.agents.models import Machine
from apps.alerts.models import Alert
from apps.tickets.models import Ticket
from apps.tickets.services import TicketAutomationService

class Command(BaseCommand):
    """
    Consolidated command to run periodic monitoring checks:
    1. Detects offline machines (no heartbeat for 5+ mins) -> raises critical alert + ticket.
    2. Escalates active high alerts (no resolved status for 15+ mins) -> raises high priority ticket.
    """
    help = 'Executa checagens periódicas de monitoramento (verificação offline e escalonamento de alertas).'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando verificações de monitoramento periódicas...")
        
        # --- TASK 1: Heartbeat / Offline Check ---
        threshold_offline = timezone.now() - timedelta(minutes=5)
        machines_to_check = Machine.objects.exclude(status='offline').filter(
            Q(last_seen__lt=threshold_offline) | Q(last_seen__isnull=True)
        )
        
        offline_count = 0
        for machine in machines_to_check:
            # Skip if registered very recently and never seen
            if machine.last_seen is None and machine.registered_at >= threshold_offline:
                continue
                
            machine.status = 'offline'
            machine.save(update_fields=['status'])
            
            # Create offline alert if not already active
            active_alert = Alert.objects.filter(
                machine=machine,
                type='machine_offline',
                is_resolved=False
            ).first()
            
            if not active_alert:
                alert = Alert.objects.create(
                    machine=machine,
                    severity='critical',
                    type='machine_offline',
                    message=f"A máquina '{machine.hostname}' perdeu a comunicação com o servidor (sem heartbeat por mais de 5 minutos)."
                )
                self.stdout.write(self.style.WARNING(f"[-] Máquina '{machine.hostname}' offline. Alerta crítico criado."))
                
                # Critical alert opens a ticket immediately
                ticket = TicketAutomationService.create_ticket_from_alert(alert)
                self.stdout.write(self.style.WARNING(f"  -> Chamado #{ticket.id} aberto de imediato."))
            else:
                # Ensure a ticket is open for the existing alert
                ticket = TicketAutomationService.create_ticket_from_alert(active_alert)
                self.stdout.write(self.style.NOTICE(f"[*] Alerta offline já ativo para '{machine.hostname}' (Chamado #{ticket.id})."))
            
            offline_count += 1
            
        # --- TASK 2: High Alerts Escalation (15 min persistence rule) ---
        threshold_high_escalation = timezone.now() - timedelta(minutes=15)
        active_high_alerts = Alert.objects.filter(
            severity='high',
            is_resolved=False,
            created_at__lte=threshold_high_escalation
        )
        
        escalated_count = 0
        for alert in active_high_alerts:
            # Check if alert already has a ticket
            ticket_exists = Ticket.objects.filter(alert=alert).exists()
            if not ticket_exists:
                # Open ticket for this high alert
                ticket = TicketAutomationService.create_ticket_from_alert(alert)
                self.stdout.write(self.style.WARNING(
                    f"[!] Alerta alto '{alert.type}' em '{alert.machine.hostname}' "
                    f"persistiu por > 15min. Escalonado para Chamado #{ticket.id}."
                ))
                escalated_count += 1
                
        self.stdout.write(self.style.SUCCESS(
            f"Verificações concluídas. {offline_count} máquina(s) offline, "
            f"{escalated_count} novo(s) chamado(s) por persistência de alerta alto."
        ))
