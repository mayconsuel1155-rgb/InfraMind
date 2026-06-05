from django.db import models
from apps.companies.models import Company
from core.encryption import encrypt_value, decrypt_value

class AIConfig(models.Model):
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT-4o / GPT-4o-mini)'),
        ('openrouter', 'OpenRouter (OpenAI-compatible)'),
        ('anthropic', 'Anthropic (Claude 3.5 Sonnet / Claude 3 Haiku)'),
        ('google', 'Google Gemini (1.5 Pro / Flash)'),
    ]

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='ai_config')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default='openai')
    model_name = models.CharField(max_length=100, default='gpt-4o-mini')
    api_key_encrypted = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    from core.managers import TenantManager
    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = "Configuração de IA"
        verbose_name_plural = "Configurações de IA"

    def __str__(self):
        return f"Configuração de IA - {self.company.name} ({self.get_provider_display()})"

    @property
    def api_key(self):
        return decrypt_value(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value):
        self.api_key_encrypted = encrypt_value(value)
