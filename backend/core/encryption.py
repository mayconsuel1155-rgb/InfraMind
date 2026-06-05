from cryptography.fernet import Fernet
from django.conf import settings

from django.core.exceptions import ImproperlyConfigured

DEFAULT_DEV_KEY = b't-cBRv8E_YpZg8Yq4Jt1s0z-l3eYgG67_3N421kL8k0='

def get_fernet():
    import sys
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    
    # In production (DEBUG=False), we enforce a custom FIELD_ENCRYPTION_KEY.
    # It must be configured and cannot be the default development key.
    is_debug = getattr(settings, 'DEBUG', True)
    is_testing = 'test' in sys.argv
    
    if not is_debug and not is_testing:
        if not key or key == DEFAULT_DEV_KEY or key == DEFAULT_DEV_KEY.decode('utf-8'):
            raise ImproperlyConfigured(
                "Segurança: FIELD_ENCRYPTION_KEY não está configurada ou está usando o valor padrão de desenvolvimento. "
                "Configure uma chave única em produção via variável de ambiente."
            )
            
    if not key:
        key = DEFAULT_DEV_KEY
    
    if isinstance(key, str):
        key = key.encode('utf-8')
    
    return Fernet(key)

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    f = get_fernet()
    return f.encrypt(value.encode('utf-8')).decode('utf-8')

def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    f = get_fernet()
    try:
        return f.decrypt(encrypted_value.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback or error handling
        return "[Erro: Não foi possível decifrar a chave de API]"
