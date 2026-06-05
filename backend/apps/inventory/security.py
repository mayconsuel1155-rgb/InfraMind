from django.utils import timezone


SECURITY_THREAT_RULES = [
    {
        "type": "security_remote_access_tool",
        "severity": "high",
        "title": "Ferramenta de acesso remoto detectada",
        "keywords": [
            "anydesk",
            "teamviewer",
            "rustdesk",
            "ultravnc",
            "tightvnc",
            "radmin",
            "screenconnect",
            "logmein",
        ],
        "message": "Ferramenta de acesso remoto encontrada no inventario. Verifique se o uso foi autorizado.",
    },
    {
        "type": "security_potential_persistence_tool",
        "severity": "critical",
        "title": "Ferramenta potencialmente invasiva detectada",
        "keywords": [
            "mimikatz",
            "metasploit",
            "meterpreter",
            "powersploit",
            "empire",
            "cobalt strike",
            "psexec",
            "wmiexec",
            "nmap",
            "masscan",
            "hydra",
        ],
        "message": "Software com assinatura potencialmente invasiva foi detectado. Investigue imediatamente.",
    },
]


def _normalize_threat(text: str) -> str:
    return " ".join((text or "").lower().split())


def build_software_threats(softwares):
    threats = []
    seen = set()

    for software in softwares or []:
        name = _normalize_threat(software.get("name", ""))
        if not name:
            continue

        for rule in SECURITY_THREAT_RULES:
            if any(keyword in name for keyword in rule["keywords"]):
                threat_id = rule["type"]
                if threat_id in seen:
                    continue
                seen.add(threat_id)
                threats.append({
                    "id": threat_id,
                    "type": rule["type"],
                    "severity": rule["severity"],
                    "title": rule["title"],
                    "message": f"{rule['message']} Encontrado: {software.get('name', 'desconhecido')}.",
                    "source": "inventory",
                })

    return threats


def sync_security_threat_alerts(machine, threats):
    from apps.alerts.models import Alert

    active_types = set()
    for threat in threats:
        alert_type = threat["type"]
        active_types.add(alert_type)
        active_alert = Alert.objects.filter(
            machine=machine,
            type=alert_type,
            is_resolved=False,
        ).first()

        if not active_alert:
            alert = Alert.objects.create(
                machine=machine,
                severity=threat["severity"],
                type=alert_type,
                message=threat["message"],
            )
            # Abrir chamado automaticamente se o alerta de segurança for crítico
            if threat["severity"] == 'critical':
                from apps.tickets.services import TicketAutomationService
                TicketAutomationService.create_ticket_from_alert(alert)

    Alert.objects.filter(
        machine=machine,
        type__startswith="security_",
        is_resolved=False,
    ).exclude(type__in=active_types).update(
        is_resolved=True,
        resolved_at=timezone.now(),
    )
