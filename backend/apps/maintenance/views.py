from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

from .models import MaintenanceReport, MaintenanceItem
from .forms import MaintenanceReportForm, MaintenanceItemFormSet

def _get_allowed_reports(user):
    if user.role == 'superadmin':
        return MaintenanceReport.objects_all.all()
    elif user.company_id:
        return MaintenanceReport.objects.all()
    return MaintenanceReport.objects.none()

@login_required
def maintenance_list_view(request):
    reports = _get_allowed_reports(request.user).order_by('-created_at')
    
    # Filtros
    status = request.GET.get('status')
    m_type = request.GET.get('type')
    
    if status:
        reports = reports.filter(status=status)
    if m_type:
        reports = reports.filter(type=m_type)

    total_cost = sum([r.total_cost for r in reports])

    context = {
        'reports': reports,
        'total_cost': total_cost,
        'completed_count': reports.filter(status='completed').count(),
        'in_progress_count': reports.filter(status='in_progress').count()
    }
    return render(request, 'maintenance/list.html', context)

@login_required
def maintenance_create_view(request):
    if request.user.role not in ('superadmin', 'admin', 'technician'):
        messages.error(request, 'Sem permissão para criar relatórios.')
        return redirect('maintenance_list')

    if request.method == 'POST':
        form = MaintenanceReportForm(request.POST, request=request)
        formset = MaintenanceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            report = form.save(commit=False)
            report.technician = request.user
            
            # Se for superadmin precisa escolher a empresa da máquina, ou a dele
            if request.user.role == 'superadmin' and report.machine:
                 report.company = report.machine.company
            else:
                 report.company = request.user.company

            report.save()
            
            formset.instance = report
            formset.save()
            
            messages.success(request, 'Relatório de manutenção criado com sucesso!')
            return redirect('maintenance_detail', pk=report.pk)
    else:
        form = MaintenanceReportForm(request=request)
        formset = MaintenanceItemFormSet()

    context = {
        'form': form,
        'formset': formset,
        'title': 'Nova Manutenção'
    }
    return render(request, 'maintenance/form.html', context)

@login_required
def maintenance_update_view(request, pk):
    report = get_object_or_404(_get_allowed_reports(request.user), pk=pk)
    
    if request.user.role not in ('superadmin', 'admin', 'technician'):
        messages.error(request, 'Sem permissão para editar relatórios.')
        return redirect('maintenance_detail', pk=pk)

    if request.method == 'POST':
        form = MaintenanceReportForm(request.POST, instance=report, request=request)
        formset = MaintenanceItemFormSet(request.POST, instance=report)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Relatório atualizado com sucesso!')
            return redirect('maintenance_detail', pk=report.pk)
    else:
        form = MaintenanceReportForm(instance=report, request=request)
        formset = MaintenanceItemFormSet(instance=report)

    context = {
        'form': form,
        'formset': formset,
        'title': f'Editar Manutenção #{report.pk}'
    }
    return render(request, 'maintenance/form.html', context)

@login_required
def maintenance_detail_view(request, pk):
    report = get_object_or_404(_get_allowed_reports(request.user), pk=pk)
    return render(request, 'maintenance/detail.html', {'report': report})

@login_required
def maintenance_print_view(request, pk):
    report = get_object_or_404(_get_allowed_reports(request.user), pk=pk)
    return render(request, 'maintenance/print.html', {'report': report})
