from django.db import models
from apps.companies.models import Company

class ComplianceRequirement(models.Model):
    article = models.CharField(max_length=50, verbose_name="Artigo/Inciso (CNJ 213)")
    description = models.TextField(verbose_name="Descrição do Requisito")
    is_mandatory = models.BooleanField(default=True, verbose_name="Obrigatório")

    class Meta:
        verbose_name = "Requisito de Conformidade"
        verbose_name_plural = "Requisitos de Conformidade"
        ordering = ['article']

    def __str__(self):
        return f"{self.article} - {self.description[:50]}"

class RiskMatrix(models.Model):
    RISK_CHOICES = [
        ('low', 'Baixo'),
        ('medium', 'Médio'),
        ('high', 'Alto'),
        ('critical', 'Crítico'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='risks', verbose_name="Empresa")
    title = models.CharField(max_length=200, verbose_name="Risco Identificado")
    impact = models.CharField(max_length=20, choices=RISK_CHOICES, verbose_name="Impacto")
    probability = models.CharField(max_length=20, choices=RISK_CHOICES, verbose_name="Probabilidade")
    mitigation_plan = models.TextField(blank=True, verbose_name="Plano de Tratamento")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False, verbose_name="Risco Tratado")

    class Meta:
        verbose_name = "Matriz de Risco"
        verbose_name_plural = "Matrizes de Risco"

    def __str__(self):
        return f"[{self.company}] {self.title} (Risco: {self.impact}/{self.probability})"

class ComplianceEvidence(models.Model):
    STATUS_CHOICES = [
        ('implemented', 'Implementado'),
        ('partial', 'Parcial'),
        ('none', 'Não Implementado'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='evidences', verbose_name="Empresa")
    requirement = models.ForeignKey(ComplianceRequirement, on_delete=models.CASCADE, related_name='evidences', verbose_name="Requisito CNJ 213")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='none', verbose_name="Status de Adequação")
    evidence_text = models.TextField(blank=True, verbose_name="Evidência (Texto/Link)")
    action_needed = models.TextField(blank=True, verbose_name="Ação Necessária")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evidência de Conformidade"
        verbose_name_plural = "Evidências de Conformidade"
        unique_together = ('company', 'requirement')

    def __str__(self):
        return f"[{self.company}] {self.requirement.article}: {self.get_status_display()}"
