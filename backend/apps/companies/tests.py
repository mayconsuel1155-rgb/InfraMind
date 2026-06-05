from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.companies.forms import UserForm
from apps.companies.models import Company


class CompanyConsoleTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Alpha Ops')
        self.superadmin = User.objects.create_superuser(
            email='root@example.com',
            password='secret123',
        )
        self.admin = User.objects.create_user(
            email='admin@alpha.com',
            password='secret123',
            company=self.company,
            role='admin',
        )

    def test_superadmin_can_create_company(self):
        client = Client()
        self.assertTrue(client.login(username='root@example.com', password='secret123'))

        response = client.post(
            reverse('management_console'),
            {
                'action': 'create_company',
                'company-name': 'Beta Cloud',
                'company-is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Company.objects.filter(name='Beta Cloud').exists())

    def test_superadmin_can_create_company_with_cnpj_and_address(self):
        client = Client()
        self.assertTrue(client.login(username='root@example.com', password='secret123'))

        response = client.post(
            reverse('management_console'),
            {
                'action': 'create_company',
                'company-name': 'Delta Tech Ltda',
                'company-cnpj': '00.000.000/0001-91',
                'company-trade_name': 'Delta Tech',
                'company-phone': '11999999999',
                'company-email': 'contato@delta.com',
                'company-address_zip_code': '01001-000',
                'company-address_street': 'Praça da Sé',
                'company-address_number': '123',
                'company-address_complement': 'Sala 4',
                'company-address_neighborhood': 'Sé',
                'company-address_city': 'São Paulo',
                'company-address_state': 'SP',
                'company-is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        company = Company.objects.get(cnpj='00.000.000/0001-91')
        self.assertEqual(company.name, 'Delta Tech Ltda')
        self.assertEqual(company.address_city, 'São Paulo')
        self.assertEqual(company.address_state, 'SP')
        self.assertEqual(company.address_street, 'Praça da Sé')

    def test_admin_user_form_inherits_company_scope(self):
        form = UserForm(
            data={
                'user-email': 'new.tech@alpha.com',
                'user-password': 'secret123',
                'user-role': 'viewer',
                'user-is_active': 'on',
            },
            current_user=self.admin,
            prefix='user',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        created = form.save()

        self.assertEqual(created.company, self.company)
        self.assertEqual(created.role, 'viewer')

    def test_admin_can_create_branch(self):
        client = Client()
        self.assertTrue(client.login(username='admin@alpha.com', password='secret123'))

        response = client.post(
            reverse('management_console'),
            {
                'action': 'create_company',
                'company-name': 'Alpha Branch',
                'company-is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        # Verify the new company was created as a branch of Alpha Ops
        branch = Company.objects_all.get(name='Alpha Branch')
        self.assertEqual(branch.parent_company, self.company)

    def test_admin_can_edit_own_company(self):
        client = Client()
        self.assertTrue(client.login(username='admin@alpha.com', password='secret123'))

        response = client.post(
            reverse('management_console'),
            {
                'action': 'edit_company',
                'company_id': self.company.id,
                'name': 'Alpha Ops Updated',
                'trade_name': 'Alpha Premium',
                'phone': '1199999999',
                'email': 'contact@alpha.com',
                'cnpj': '11.222.333/0001-44',
                'is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Alpha Ops Updated')
        self.assertEqual(self.company.cnpj, '11.222.333/0001-44')

    def test_tenant_queryset_includes_branches(self):
        # Create a branch for Alpha Ops
        branch = Company.objects_all.create(name='Alpha Branch', parent_company=self.company)
        # Create another unrelated company
        other_company = Company.objects_all.create(name='Beta Tech')

        # Simulate tenant setting via manager/queryset directly
        from core.tenancy import set_current_tenant, reset_current_tenant
        token = set_current_tenant(self.company)
        try:
            visible_companies = list(Company.objects.all())
            self.assertIn(self.company, visible_companies)
            self.assertIn(branch, visible_companies)
            self.assertNotIn(other_company, visible_companies)
        finally:
            reset_current_tenant(token)

    def test_admin_cannot_edit_other_company(self):
        other_company = Company.objects_all.create(name='Beta Tech')
        client = Client()
        self.assertTrue(client.login(username='admin@alpha.com', password='secret123'))

        response = client.post(
            reverse('management_console'),
            {
                'action': 'edit_company',
                'company_id': other_company.id,
                'name': 'Hacked Name',
                'is_active': 'on',
            },
        )

        # Should be forbidden (403)
        self.assertEqual(response.status_code, 403)
        other_company.refresh_from_db()
        self.assertNotEqual(other_company.name, 'Hacked Name')
