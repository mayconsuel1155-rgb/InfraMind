from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ComplianceRequirement, RiskMatrix, ComplianceEvidence

@login_required
def compliance_dashboard(request):
    company = request.user.company
    if not company:
        return render(request, 'compliance/dashboard.html', {'error': 'Usuário sem empresa vinculada'})

    # For MVP, auto-create base requirements if they don't exist
    if not ComplianceRequirement.objects.exists():
        reqs = [
            ("Art. 10", "Controle de acesso rigoroso com MFA e trilha de auditoria", True),
            ("Art. 12", "Política de Retenção e Descarte Seguro de Dados (LGPD)", True),
            ("Art. 15", "Plano de Continuidade de Negócios (RPO/RTO)", True),
            ("Art. 18", "Matriz de Riscos de TI documentada", True),
            ("Art. 20", "Testes periódicos e Evidências geradas automaticamente", True),
        ]
        for article, desc, mandatory in reqs:
            ComplianceRequirement.objects.create(article=article, description=desc, is_mandatory=mandatory)

    requirements = ComplianceRequirement.objects.all()
    evidences = ComplianceEvidence.objects.filter(company=company)
    
    # Auto-create empty evidences for requirements without one for this company
    for req in requirements:
        if not evidences.filter(requirement=req).exists():
            ComplianceEvidence.objects.create(company=company, requirement=req, status='none')

    evidences = ComplianceEvidence.objects.filter(company=company).select_related('requirement')
    
    total = evidences.count()
    implemented = evidences.filter(status='implemented').count()
    partial = evidences.filter(status='partial').count()
    none = evidences.filter(status='none').count()

    # Simplistic calculation: implemented=100%, partial=50%, none=0%
    if total > 0:
        score = ((implemented * 1) + (partial * 0.5)) / total * 100
    else:
        score = 0

    risks = RiskMatrix.objects.filter(company=company)

    context = {
        'evidences': evidences,
        'risks': risks,
        'score': round(score, 1),
        'implemented': implemented,
        'partial': partial,
        'none': none,
        'total': total
    }
    
    return render(request, 'compliance/dashboard.html', context)

@login_required
def report_executive(request):
    company = request.user.company
    evidences = ComplianceEvidence.objects.filter(company=company).select_related('requirement')
    risks = RiskMatrix.objects.filter(company=company)
    
    total = evidences.count()
    implemented = evidences.filter(status='implemented').count()
    partial = evidences.filter(status='partial').count()
    
    score = ((implemented * 1) + (partial * 0.5)) / total * 100 if total > 0 else 0

    context = {
        'company': company,
        'score': round(score, 1),
        'evidences': evidences,
        'risks': risks,
        'date': __import__('datetime').date.today()
    }
    return render(request, 'compliance/report_executive.html', context)

@login_required
def report_audit(request):
    company = request.user.company
    from apps.audit.models import GlobalAuditLog
    logs = GlobalAuditLog.objects.filter(company=company).select_related('operator')[:500] # Limite para o relatório MVP
    
    context = {
        'company': company,
        'logs': logs,
        'date': __import__('datetime').date.today()
    }
    return render(request, 'compliance/report_audit.html', context)
