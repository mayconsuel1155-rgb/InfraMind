from rest_framework import authentication
from rest_framework import exceptions
from django.core.exceptions import ValidationError
from apps.agents.models import Machine

class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for DRF.
    Validates the 'Authorization: ApiKey <uuid>' header.
    If valid, returns the Machine object as request.user.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'apikey':
            return None

        api_key_str = parts[1]
        try:
            machine = Machine.objects.select_related('company').get(api_key=api_key_str)
        except (Machine.DoesNotExist, ValidationError, ValueError):
            raise exceptions.AuthenticationFailed('Chave de API inválida ou máquina não cadastrada.')

        if not machine.company.is_active:
            raise exceptions.AuthenticationFailed('Empresa inativa. Acesso negado.')

        # Return (machine, auth) where auth is the key or None
        return (machine, api_key_str)
