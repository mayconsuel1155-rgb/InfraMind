from datetime import timedelta
from unittest.mock import patch
from django.template.context import Context

# Workaround for Python 3.14 compatibility with Django Context copy
def _safe_context_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.dicts = self.dicts[:]
    if hasattr(self, 'request'):
        duplicate.request = self.request
    return duplicate
Context.__copy__ = _safe_context_copy

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.alerts.models import Alert
from apps.agents.models import Machine
from apps.companies.models import Company
from apps.tickets.models import Ticket, TicketWorkLog
from apps.tickets.services import TicketReportService

User = get_user_model()


class TicketWorkLogTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Support Co')
        self.user = User.objects.create_user(
            email='tech@support.com',
            password='secret123',
            company=self.company,
            role='technician',
        )
        self.ticket = Ticket.objects.create(
            company=self.company,
            title='Incidente de rede',
            description='Sem acesso à internet.',
            priority='high',
            status='open',
        )

    def test_pause_calculates_duration(self):
        log = TicketWorkLog.objects.create(ticket=self.ticket, user=self.user, note='Iniciando análise')
        TicketWorkLog.objects.filter(pk=log.pk).update(started_at=timezone.now() - timedelta(minutes=42))
        log.refresh_from_db()

        log.pause()

        self.assertFalse(log.is_active)
        self.assertGreaterEqual(log.duration_seconds, 2500)

    def test_timer_play_and_pause_flow(self):
        client = self.client
        self.assertTrue(client.login(username='tech@support.com', password='secret123'))

        play_response = client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {
                'action': 'timer_play',
                'note': 'Validando serviços da estação',
            },
        )
        self.assertEqual(play_response.status_code, 302)
        self.assertTrue(TicketWorkLog.objects.filter(ticket=self.ticket, user=self.user, is_active=True).exists())

        pause_response = client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {
                'action': 'timer_pause',
                'note': 'Servico DNS reiniciado',
            },
        )
        self.assertEqual(pause_response.status_code, 302)
        log = TicketWorkLog.objects.get(ticket=self.ticket, user=self.user)
        self.assertFalse(log.is_active)
        self.assertIn('Servico DNS reiniciado', log.note)

    def test_timer_play_and_pause_htmx_flow(self):
        client = self.client
        self.assertTrue(client.login(username='tech@support.com', password='secret123'))

        play_response = client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {
                'action': 'timer_play',
                'note': 'Validando via HTMX',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(play_response.status_code, 200)
        self.assertTemplateUsed(play_response, 'tickets/partials/timer_section.html')
        self.assertTrue(TicketWorkLog.objects.filter(ticket=self.ticket, user=self.user, is_active=True).exists())

        pause_response = client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {
                'action': 'timer_pause',
                'note': 'Pausa via HTMX',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(pause_response.status_code, 200)
        self.assertTemplateUsed(pause_response, 'tickets/partials/timer_section.html')
        log = TicketWorkLog.objects.get(ticket=self.ticket, user=self.user)
        self.assertFalse(log.is_active)

    def test_manual_ticket_creation(self):
        client = self.client
        self.assertTrue(client.login(username='tech@support.com', password='secret123'))

        # Create a Machine for the support company to link
        machine = Machine.objects.create(
            company=self.company,
            hostname='srv-prod-01',
            ip_address='192.168.1.5',
            operating_system='Windows Server',
            cpu_model='Intel Xeon',
            cpu_cores=16,
            ram_total_gb=64,
            disk_total_gb=1024,
            status='online'
        )

        response = client.post(
            reverse('tickets_list'),
            {
                'title': 'Chamado de teste manual',
                'description': 'Problema no acesso ao banco de dados local.',
                'priority': 'high',
                'machine': machine.id,
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ticket.objects.filter(title='Chamado de teste manual', machine=machine).exists())

        ticket = Ticket.objects.get(title='Chamado de teste manual')
        self.assertEqual(ticket.company, self.company)
        self.assertEqual(ticket.priority, 'high')
        self.assertEqual(ticket.status, 'open')

    def test_manual_ticket_creation_by_superadmin(self):
        # Create a superadmin
        superadmin = User.objects.create_superuser(
            email='super@inframind.com',
            password='secret123',
        )
        # Create another company and user
        other_company = Company.objects.create(name='Other Company')
        other_user = User.objects.create_user(
            email='tech@other.com',
            password='secret123',
            company=other_company,
            role='technician'
        )

        client = self.client
        self.assertTrue(client.login(username='super@inframind.com', password='secret123'))

        response = client.post(
            reverse('tickets_list'),
            {
                'title': 'Chamado por superadmin',
                'description': 'Abertura manual de teste.',
                'priority': 'medium',
                'company': other_company.id,
                'assigned_to': other_user.id,
            }
        )

        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title='Chamado por superadmin')
        self.assertEqual(ticket.company, other_company)
        self.assertEqual(ticket.assigned_to, other_user)
        self.assertEqual(ticket.priority, 'medium')
        self.assertEqual(ticket.status, 'open')



class TicketReportServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Ops Co')
        self.user = User.objects.create_user(
            email='admin@ops.com',
            password='secret123',
            company=self.company,
            role='admin',
        )
        self.machine_alert = Alert.objects.create(
            machine=Machine.objects.create(
                company=self.company,
                hostname='ws-09',
                ip_address='10.10.10.9',
                operating_system='Windows 11',
                cpu_model='Intel',
                cpu_cores=8,
                ram_total_gb=16,
                disk_total_gb=512,
                status='online',
            ),
            severity='high',
            type='firewall_disabled',
            message='Firewall desativado.',
        )
        self.ticket = Ticket.objects.create(
            company=self.company,
            alert=self.machine_alert,
            title='Firewall desativado',
            description='Verificar política de segurança.',
            priority='high',
            status='in_progress',
        )
        TicketWorkLog.objects.create(
            ticket=self.ticket,
            user=self.user,
            note='Validei o serviço de firewall e confirmei a regra aplicada.',
            is_active=False,
            duration_seconds=1800,
        )

    @patch('apps.tickets.services.AIService.generate_completion')
    def test_generate_report_persists_ai_output(self, mock_generate_completion):
        mock_generate_completion.return_value = '# Relatório\n\nTudo certo.'

        report = TicketReportService.generate_report(self.ticket)

        self.assertIn('Relatório', report)
        self.ticket.refresh_from_db()
        self.assertIn('Tudo certo.', self.ticket.ai_report)
        self.assertIsNotNone(self.ticket.ai_report_generated_at)

    def test_generate_report_without_notes_raises_value_error(self):
        # Create a new ticket without work logs / notes
        empty_ticket = Ticket.objects.create(
            company=self.company,
            title='Incidente vazio',
            description='Sem notas.',
            priority='low',
            status='open',
        )
        
        with self.assertRaises(ValueError) as ctx:
            TicketReportService.generate_report(empty_ticket)
        
        self.assertIn("Não é possível gerar o relatório sem apontamentos técnicos detalhados.", str(ctx.exception))
