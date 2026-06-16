import json
from django.utils.deprecation import MiddlewareMixin
from apps.audit.models import GlobalAuditLog

class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Ignorar requests que não estão logados ou se for GET genérico não sensível
        # Para fins de MVP, vamos logar todos os POST/PUT/PATCH/DELETE e rotas sensíveis
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return

        method = request.method
        path = request.path

        # Ignore static and media paths if they somehow pass through Django
        if path.startswith('/static/') or path.startswith('/media/'):
            return

        is_sensitive_read = method == 'GET' and ('/export' in path or '/download' in path)
        is_write = method in ['POST', 'PUT', 'PATCH', 'DELETE']

        if is_write or is_sensitive_read:
            action = f"{method} Request"
            if method == 'POST':
                action = "Criação / Atualização"
            elif method == 'DELETE':
                action = "Exclusão"
            elif method == 'PUT' or method == 'PATCH':
                action = "Edição"
            
            if is_sensitive_read:
                action = "Visualização Sensível / Exportação"

            # Parse simple body details safely
            details = {}
            if method in ['POST', 'PUT', 'PATCH']:
                try:
                    # Tentar pegar os dados da request (não ler request.body diretamente se for multipart)
                    if request.POST:
                        # Copy QueryDict and mask password fields
                        safe_data = request.POST.copy()
                        for key in safe_data.keys():
                            if 'password' in key.lower() or 'secret' in key.lower() or 'token' in key.lower() or 'mfa' in key.lower():
                                safe_data[key] = '***'
                        details = dict(safe_data)
                except Exception:
                    details = {"info": "Corpo da requisição não processável no middleware"}

            GlobalAuditLog.objects.create(
                operator=request.user,
                company=request.user.company,
                action=action,
                path=path,
                method=method,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                details=details
            )
