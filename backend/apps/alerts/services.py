from django.utils import timezone
from apps.alerts.models import Alert

class RulesEngineService:
    """
    Evaluates system metrics against configured thresholds.
    Creates alerts with suppression (prevents duplicates) and handles auto-resolution.
    """
    @classmethod
    def evaluate_metrics(cls, metric):
        machine = metric.machine
        company = machine.company
        
        # Load thresholds or create defaults for this company
        from apps.alerts.models import MonitoringThreshold
        thresholds, _ = MonitoringThreshold.objects.get_or_create(
            company=company,
            defaults={
                'cpu_limit': 95.0,
                'ram_limit': 90.0,
                'disk_limit': 80.0
            }
        )
        
        cpu_lim = thresholds.cpu_limit
        ram_lim = thresholds.ram_limit
        disk_lim = thresholds.disk_limit
        
        # Rule 1: CPU (severity: high, type: cpu_high)
        cls._check_rule(
            machine=machine,
            condition=metric.cpu_percent > cpu_lim,
            severity='high',
            alert_type='cpu_high',
            message=f"Uso de CPU elevado: {metric.cpu_percent}% (limite {cpu_lim}%)"
        )

        # Rule 2: RAM (severity: high, type: ram_high)
        cls._check_rule(
            machine=machine,
            condition=metric.ram_percent > ram_lim,
            severity='high',
            alert_type='ram_high',
            message=f"Uso de Memória RAM elevado: {metric.ram_percent}% (limite {ram_lim}%)"
        )

        # Rule 3: Disk (severity: low, type: disk_warning)
        cls._check_rule(
            machine=machine,
            condition=metric.disk_percent > disk_lim,
            severity='low',
            alert_type='disk_warning',
            message=f"Espaço em disco com uso elevado: {metric.disk_percent}% (limite {disk_lim}%)"
        )

        # Rule 4 & 5: Security Alerts (Antivirus / Firewall)
        from apps.inventory.models import SecurityStatus
        try:
            sec_status = SecurityStatus.objects.get(machine=machine)
            
            cls._check_rule(
                machine=machine,
                condition=not sec_status.antivirus_active,
                severity='critical',
                alert_type='antivirus_disabled',
                message="Segurança Crítica: O antivírus corporativo ou proteção em tempo real está desativado."
            )
            
            cls._check_rule(
                machine=machine,
                condition=not sec_status.firewall_active,
                severity='high',
                alert_type='firewall_disabled',
                message="Alerta de Segurança: O firewall de rede do sistema está desativado."
            )
        except SecurityStatus.DoesNotExist:
            pass

    @classmethod
    def _check_rule(cls, machine, condition, severity, alert_type, message):
        active_alert = Alert.objects.filter(
            machine=machine,
            type=alert_type,
            is_resolved=False
        ).first()

        if condition:
            # Condition met: alert should be active
            if not active_alert:
                alert = Alert.objects.create(
                    machine=machine,
                    severity=severity,
                    type=alert_type,
                    message=message
                )
                cls._update_machine_status(machine)
                
                # Immediately open ticket if alert is critical
                if severity == 'critical':
                    from apps.tickets.services import TicketAutomationService
                    TicketAutomationService.create_ticket_from_alert(alert)
        else:
            # Condition not met: resolve alert if it is currently active
            if active_alert:
                active_alert.is_resolved = True
                active_alert.resolved_at = timezone.now()
                active_alert.save()
                cls._update_machine_status(machine)

    @classmethod
    def _update_machine_status(cls, machine):
        # We only update to critical/warning status if the machine is online.
        # If the machine is offline, we keep the status as offline.
        if machine.status == 'offline':
            return
            
        active_alerts = Alert.objects.filter(machine=machine, is_resolved=False)
        
        if active_alerts.filter(severity='critical').exists():
            machine.status = 'critical'
        elif active_alerts.filter(severity='high').exists():
            machine.status = 'warning'
        else:
            machine.status = 'online'
            
        machine.save(update_fields=['status'])
