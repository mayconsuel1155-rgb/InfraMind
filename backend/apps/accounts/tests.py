from django.template.context import Context

# Workaround for Python 3.14 compatibility with Django Context copy
def _safe_context_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.dicts = self.dicts[:]
    if hasattr(self, 'request'):
        duplicate.request = self.request
    return duplicate
Context.__copy__ = _safe_context_copy

from django.contrib.auth import authenticate
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from apps.accounts.models import User, LGPDAuditLog
from apps.companies.models import Company
import json

class EmailBackendTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa A", slug="empresa-a")
        self.user = User.objects.create_user(
            email='tech@example.com',
            password='secret123',
            role='viewer',
            company=self.company,
        )

    def test_authenticate_with_email(self):
        user = authenticate(email='tech@example.com', password='secret123')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, self.user.email)


@override_settings(TEST_BYPASS_LGPD=False)
class LGPDComplianceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name="Empresa Teste", slug="empresa-teste")
        
        # User without consent
        self.user_no_consent = User.objects.create_user(
            email='no_consent@teste.com',
            password='password123',
            role='viewer',
            company=self.company,
        )
        # User with consent
        self.user_with_consent = User.objects.create_user(
            email='with_consent@teste.com',
            password='password123',
            role='technician',
            company=self.company,
            lgpd_accepted_terms=True,
        )
        # Admin
        self.admin_user = User.objects.create_user(
            email='admin@teste.com',
            password='password123',
            role='admin',
            company=self.company,
            lgpd_accepted_terms=True,
        )
        
        # Another company and its user
        self.other_company = Company.objects.create(name="Outra Empresa", slug="outra-empresa")
        self.other_user = User.objects.create_user(
            email='other@outra.com',
            password='password123',
            role='viewer',
            company=self.other_company,
            lgpd_accepted_terms=True,
        )

    def test_middleware_redirects_user_without_consent(self):
        self.client.force_login(self.user_no_consent)
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('lgpd_consent'))

    def test_middleware_does_not_redirect_user_with_consent(self):
        self.client.force_login(self.user_with_consent)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_consent_acceptance_flow(self):
        self.client.force_login(self.user_no_consent)
        
        # Check consent page loaded
        response = self.client.get(reverse('lgpd_consent'))
        self.assertEqual(response.status_code, 200)
        
        # Submit consent
        response = self.client.post(reverse('lgpd_consent'))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Verify user model is updated
        self.user_no_consent.refresh_from_db()
        self.assertTrue(self.user_no_consent.lgpd_accepted_terms)
        self.assertIsNotNone(self.user_no_consent.lgpd_accepted_at)
        
        # Verify audit log was created
        log = LGPDAuditLog.objects.filter(target_email=self.user_no_consent.email, action='consent_accept').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.operator, self.user_no_consent)

    def test_data_portability_export(self):
        # 1. User exporting own data
        self.client.force_login(self.user_with_consent)
        response = self.client.get(reverse('lgpd_export_own_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['user_profile']['email'], self.user_with_consent.email)
        
        # Verify audit log
        self.assertTrue(LGPDAuditLog.objects.filter(target_email=self.user_with_consent.email, action='data_export').exists())
        
        # 2. Admin exporting other user's data from same company
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('lgpd_export_user_data', args=[self.user_with_consent.id]))
        self.assertEqual(response.status_code, 200)
        
        # 3. Admin trying to export other company's user data
        response = self.client.get(reverse('lgpd_export_user_data', args=[self.other_user.id]))
        self.assertEqual(response.status_code, 403)

    def test_anonymization(self):
        self.client.force_login(self.admin_user)
        
        # Anonymize user from same company
        response = self.client.get(reverse('lgpd_anonymize_user', args=[self.user_with_consent.id]))
        self.assertRedirects(response, reverse('management_console'))
        
        # Verify target user fields
        self.user_with_consent.refresh_from_db()
        self.assertFalse(self.user_with_consent.is_active)
        self.assertTrue(self.user_with_consent.email.startswith('anonimo_'))
        self.assertFalse(self.user_with_consent.has_usable_password())
        
        # Verify audit log was created with the original email
        log = LGPDAuditLog.objects.filter(target_email='with_consent@teste.com', action='anonymization').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.operator, self.admin_user)
        
        # Admin trying to anonymize someone from other company (invisible due to tenancy)
        response = self.client.get(reverse('lgpd_anonymize_user', args=[self.other_user.id]))
        self.assertEqual(response.status_code, 404)

    def test_password_reset_by_admin(self):
        self.client.force_login(self.admin_user)
        
        # Reset password for same company user
        response = self.client.post(reverse('user_reset_password', args=[self.user_with_consent.id]), {
            'new_password': 'newSecurePassword123!'
        })
        self.assertRedirects(response, reverse('management_console'))
        
        # Verify password actually changed
        self.user_with_consent.refresh_from_db()
        self.assertTrue(self.user_with_consent.check_password('newSecurePassword123!'))
        
        # Verify LGPDAuditLog is generated
        log = LGPDAuditLog.objects.filter(target_email=self.user_with_consent.email, action='user_update').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.operator, self.admin_user)
        self.assertIn("Senha de acesso reiniciada", log.details)
        
        # Admin trying to reset other company's user password (invisible due to tenancy)
        response = self.client.post(reverse('user_reset_password', args=[self.other_user.id]), {
            'new_password': 'otherPassword123'
        })
        self.assertEqual(response.status_code, 404)
        
        # Regular user trying to reset password (forbidden)
        self.client.force_login(self.user_with_consent)
        response = self.client.post(reverse('user_reset_password', args=[self.user_no_consent.id]), {
            'new_password': 'somePassword123'
        })
        self.assertEqual(response.status_code, 403)
