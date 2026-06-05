from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.alerts.models import Alert
from apps.agents.models import Machine
from apps.inventory.views import AgentInventoryView
from apps.companies.models import Company
from apps.inventory.security import build_software_threats, sync_security_threat_alerts


class InventorySecurityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Security Co")
        self.machine = Machine.objects.create(
            company=self.company,
            hostname="ws-01",
            ip_address="10.0.0.10",
            operating_system="Windows 11",
            cpu_model="Intel",
            cpu_cores=8,
            ram_total_gb=16,
            disk_total_gb=512,
            status="online",
        )

    def test_build_software_threats_detects_remote_access_and_intrusion_tools(self):
        threats = build_software_threats(
            [
                {"name": "AnyDesk"},
                {"name": "Mimikatz"},
                {"name": "Notepad++"},
            ]
        )

        threat_types = {item["type"] for item in threats}

        self.assertIn("security_remote_access_tool", threat_types)
        self.assertIn("security_potential_persistence_tool", threat_types)
        self.assertEqual(len(threats), 2)

    def test_sync_security_threat_alerts_creates_and_resolves_security_alerts(self):
        threats = [
            {
                "type": "security_remote_access_tool",
                "severity": "high",
                "title": "Ferramenta de acesso remoto detectada",
                "message": "AnyDesk encontrado.",
                "source": "inventory",
            }
        ]

        sync_security_threat_alerts(self.machine, threats)
        self.assertTrue(
            Alert.objects.filter(machine=self.machine, type="security_remote_access_tool", is_resolved=False).exists()
        )

        sync_security_threat_alerts(self.machine, [])
        self.assertTrue(
            Alert.objects.filter(machine=self.machine, type="security_remote_access_tool", is_resolved=True).exists()
        )

    def test_inventory_endpoint_accepts_threat_indicators_payload(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/api/agent/inventory",
            {
                "softwares": [
                    {"name": "AnyDesk", "version": "1.0", "publisher": "AnyDesk"},
                    {"name": "Notepad++", "version": "8.0", "publisher": "GPL"},
                ],
                "threat_indicators": [
                    {
                        "type": "security_manual_review",
                        "severity": "high",
                        "title": "Indicador manual",
                        "message": "Indicador enviado pelo agente.",
                        "source": "process",
                    }
                ],
            },
            format="json",
        )
        force_authenticate(request, user=self.machine)

        response = AgentInventoryView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["threats_detected"], 2)
        self.assertTrue(
            Alert.objects.filter(machine=self.machine, type="security_remote_access_tool", is_resolved=False).exists()
        )
