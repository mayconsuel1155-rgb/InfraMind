from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.agents.models import Machine
from apps.agents.views import AgentMetricsView
from apps.alerts.models import Alert
from apps.companies.models import Company
from apps.inventory.models import SecurityStatus


class AgentMetricsSecurityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Ops Co")
        self.machine = Machine.objects.create(
            company=self.company,
            hostname="ws-02",
            ip_address="10.0.0.20",
            operating_system="Windows 11",
            cpu_model="Intel",
            cpu_cores=8,
            ram_total_gb=16,
            disk_total_gb=512,
            status="online",
        )

    def test_metrics_view_accepts_threat_indicators_and_creates_alerts(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/api/agent/metrics",
            {
                "cpu_percent": 12.5,
                "ram_percent": 33.0,
                "disk_percent": 41.0,
                "antivirus_active": True,
                "firewall_active": True,
                "threat_indicators": [
                    {
                        "type": "security_encoded_powershell",
                        "severity": "critical",
                        "title": "PowerShell codificado em execucao",
                        "message": "Comando codificado detectado.",
                        "source": "process",
                    }
                ],
            },
            format="json",
        )
        force_authenticate(request, user=self.machine)

        response = AgentMetricsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Alert.objects.filter(machine=self.machine, type="security_encoded_powershell", is_resolved=False).exists()
        )
        self.assertTrue(SecurityStatus.objects.filter(machine=self.machine, antivirus_active=True, firewall_active=True).exists())

    def test_metrics_view_accepts_network_threat_and_creates_ticket(self):
        from apps.tickets.models import Ticket

        factory = APIRequestFactory()
        request = factory.post(
            "/api/agent/metrics",
            {
                "cpu_percent": 10.0,
                "ram_percent": 20.0,
                "disk_percent": 30.0,
                "antivirus_active": True,
                "firewall_active": True,
                "threat_indicators": [
                    {
                        "type": "security_suspicious_network_connection",
                        "severity": "critical",
                        "title": "Conexão de rede suspeita detectada",
                        "message": "Processo estabeleceu uma conexão TCP com a porta remota 4444.",
                        "source": "network",
                    }
                ],
            },
            format="json",
        )
        force_authenticate(request, user=self.machine)

        response = AgentMetricsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        
        # Verify alert is created
        alert = Alert.objects.filter(
            machine=self.machine,
            type="security_suspicious_network_connection",
            is_resolved=False
        ).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "critical")
        
        # Verify ticket is automatically created for critical threat alert
        ticket = Ticket.objects.filter(
            alert=alert,
            status="open"
        ).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.priority, "critical")
