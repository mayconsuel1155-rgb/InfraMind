import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from core.tenancy import set_current_tenant, reset_current_tenant
from apps.companies.models import Company
from apps.agents.models import Machine

User = get_user_model()

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = None
        company = None

        # 1. Session Auth (Web UI)
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.role != 'superadmin':
                company = getattr(request.user, 'company', None)
        else:
            # 2. Authorization Header Auth (API)
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2:
                    auth_type = parts[0].lower()
                    auth_val = parts[1]
                    
                    if auth_type == 'apikey':
                        try:
                            # Query globally using objects_all manager (defined later)
                            machine = Machine.objects_all.get(api_key=auth_val)
                            company = machine.company
                        except Exception:
                            pass
                    elif auth_type == 'bearer':
                        try:
                            payload = jwt.decode(auth_val, settings.SECRET_KEY, algorithms=['HS256'])
                            user_id = payload.get('user_id')
                            if user_id:
                                user = User.objects.get(id=user_id)
                                if user.role != 'superadmin':
                                    company = user.company
                        except Exception:
                            pass

        if company and company.is_active:
            token = set_current_tenant(company)

        try:
            response = self.get_response(request)
        finally:
            if token:
                reset_current_tenant(token)

        return response


from django.shortcuts import redirect
from django.urls import reverse

class LGPDConsentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Bypass in tests if the bypass setting is enabled
            if getattr(settings, 'TEST_BYPASS_LGPD', False):
                return self.get_response(request)

            # Bypass logic for exempt urls: lgpd_consent view, logout, static files, media, admin, and api endpoints
            exempt_urls = [
                reverse('lgpd_consent'),
                reverse('logout'),
            ]
            path = request.path
            is_exempt = (
                any(path == url for url in exempt_urls)
                or path.startswith('/static/')
                or path.startswith('/media/')
                or path.startswith('/admin/')
                or path.startswith('/api/')
            )
            
            if not is_exempt and not getattr(request.user, 'lgpd_accepted_terms', False):
                return redirect('lgpd_consent')

        return self.get_response(request)
