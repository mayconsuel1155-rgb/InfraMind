import secrets
from django.db import models
from django.utils.text import slugify

class Company(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.FileField(upload_to='company_logos/', null=True, blank=True, verbose_name="Logotipo")
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, verbose_name="CNPJ")
    trade_name = models.CharField(max_length=200, null=True, blank=True, verbose_name="Nome Fantasia")
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefone")
    email = models.EmailField(null=True, blank=True, verbose_name="E-mail")
    
    # Address fields
    address_zip_code = models.CharField(max_length=9, null=True, blank=True, verbose_name="CEP")
    address_street = models.CharField(max_length=200, null=True, blank=True, verbose_name="Logradouro")
    address_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="Número")
    address_complement = models.CharField(max_length=100, null=True, blank=True, verbose_name="Complemento")
    address_neighborhood = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    address_city = models.CharField(max_length=100, null=True, blank=True, verbose_name="Cidade")
    address_state = models.CharField(max_length=2, null=True, blank=True, verbose_name="Estado")
    
    registration_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    mfa_enforced = models.BooleanField(default=False, verbose_name="MFA Obrigatório para Usuários")
    parent_company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches',
        verbose_name="Matriz (Caso esta seja uma filial)"
    )

    from core.managers import TenantManager
    objects = TenantManager()
    objects_all = models.Manager()

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.registration_token:
            self.registration_token = secrets.token_hex(16)
        super().save(*args, **kwargs)


