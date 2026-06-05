from django.template.context import Context

# Workaround for Python 3.14 compatibility with Django Context copy
def _safe_context_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.dicts = self.dicts[:]
    if hasattr(self, 'request'):
        duplicate.request = self.request
    return duplicate
Context.__copy__ = _safe_context_copy

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from apps.agents.models import Machine
from apps.companies.models import Company
from apps.monitoring.models import Metric
from apps.alerts.models import Alert
from apps.tickets.models import Ticket
from apps.inventory.models import InstalledSoftware, SecurityStatus
from django.utils import timezone

User = get_user_model()

class MachineDeleteViewTests(TestCase):
    def setUp(self):
        # Create Companies
        self.company_a = Company.objects.create(name="Empresa A", slug="empresa-a")
        self.company_b = Company.objects.create(name="Empresa B", slug="empresa-b")

        # Create Users for Company A
        self.superadmin = User.objects.create_superuser(
            email="super@inframind.com",
            password="password123"
        )
        self.admin_a = User.objects.create_user(
            email="admin_a@empresa_a.com",
            password="password123",
            company=self.company_a,
            role="admin"
        )
        self.tech_a = User.objects.create_user(
            email="tech_a@empresa_a.com",
            password="password123",
            company=self.company_a,
            role="technician"
        )
        self.viewer_a = User.objects.create_user(
            email="viewer_a@empresa_a.com",
            password="password123",
            company=self.company_a,
            role="viewer"
        )

        # Create Admin for Company B
        self.admin_b = User.objects.create_user(
            email="admin_b@empresa_b.com",
            password="password123",
            company=self.company_b,
            role="admin"
        )

        # Create Machines
        self.machine_a = Machine.objects.create(
            company=self.company_a,
            hostname="maquina-a",
            ip_address="192.168.1.10",
            operating_system="Windows 11",
            cpu_model="AMD Ryzen",
            cpu_cores=6,
            ram_total_gb=16.0,
            disk_total_gb=256.0,
            status="online"
        )
        self.machine_b = Machine.objects.create(
            company=self.company_b,
            hostname="maquina-b",
            ip_address="192.168.2.15",
            operating_system="Windows 10",
            cpu_model="Intel Core i5",
            cpu_cores=4,
            ram_total_gb=8.0,
            disk_total_gb=240.0,
            status="online"
        )

        # Create Related Records for Machine A to test cascades
        self.metric_a = Metric.objects.create(
            machine=self.machine_a,
            cpu_percent=45.0,
            ram_percent=60.0,
            disk_percent=30.0,
            collected_at=timezone.now()
        )
        self.alert_a = Alert.objects.create(
            machine=self.machine_a,
            severity="high",
            type="cpu_high",
            message="Uso de CPU elevado."
        )
        self.software_a = InstalledSoftware.objects.create(
            machine=self.machine_a,
            name="Google Chrome",
            version="120.0"
        )
        self.security_a = SecurityStatus.objects.create(
            machine=self.machine_a,
            antivirus_active=True,
            firewall_active=True
        )
        self.ticket_a = Ticket.objects.create(
            company=self.company_a,
            machine=self.machine_a,
            alert=self.alert_a,
            title="Chamado de CPU alta",
            description="Investigar CPU da máquina.",
            priority="high",
            status="open"
        )

    def test_admin_can_delete_own_company_machine(self):
        self.client.login(email="admin_a@empresa_a.com", password="password123")
        url = reverse("machine_delete", args=[self.machine_a.pk])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("machine_list"))
        
        # Verify machine is deleted
        self.assertFalse(Machine.objects.filter(pk=self.machine_a.pk).exists())
        
        # Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("foi excluída e descartada com sucesso", str(messages[0]))

    def test_technician_cannot_delete_machine(self):
        self.client.login(email="tech_a@empresa_a.com", password="password123")
        url = reverse("machine_delete", args=[self.machine_a.pk])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Machine.objects.filter(pk=self.machine_a.pk).exists())

    def test_viewer_cannot_delete_machine(self):
        self.client.login(email="viewer_a@empresa_a.com", password="password123")
        url = reverse("machine_delete", args=[self.machine_a.pk])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Machine.objects.filter(pk=self.machine_a.pk).exists())

    def test_admin_cannot_delete_other_company_machine(self):
        # Admin A tries to delete Machine B (Company B)
        self.client.login(email="admin_a@empresa_a.com", password="password123")
        url = reverse("machine_delete", args=[self.machine_b.pk])
        
        response = self.client.post(url)
        # Should return 404 because get_company_scope filters it out from the queryset
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Machine.objects.filter(pk=self.machine_b.pk).exists())

    def test_superadmin_can_delete_any_machine(self):
        self.client.login(email="super@inframind.com", password="password123")
        url = reverse("machine_delete", args=[self.machine_b.pk])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Machine.objects.filter(pk=self.machine_b.pk).exists())

    def test_cascading_deletes_but_preserves_tickets_as_null(self):
        self.client.login(email="admin_a@empresa_a.com", password="password123")
        url = reverse("machine_delete", args=[self.machine_a.pk])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Verify cascades
        self.assertFalse(Metric.objects.filter(pk=self.metric_a.pk).exists())
        self.assertFalse(Alert.objects.filter(pk=self.alert_a.pk).exists())
        self.assertFalse(InstalledSoftware.objects.filter(pk=self.software_a.pk).exists())
        self.assertFalse(SecurityStatus.objects.filter(pk=self.security_a.pk).exists())

        # Verify ticket still exists, but machine foreign key is SET_NULL
        self.ticket_a.refresh_from_db()
        self.assertIsNotNone(self.ticket_a)
        self.assertIsNone(self.ticket_a.machine)
        self.assertIsNone(self.ticket_a.alert)
