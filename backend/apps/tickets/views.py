from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.tickets.models import Ticket, TicketWorkLog
from apps.tickets.services import TicketReportService
from apps.tickets.forms import TicketManualForm

User = get_user_model()


def get_tickets_scope(user):
    """Return tickets and users filtered by tenancy unless the user is superadmin."""
    if user.role == 'superadmin':
        return Ticket.objects.all(), User.objects.all()

    if not user.company:
        return Ticket.objects.none(), User.objects.none()

    tickets = Ticket.objects.filter(company=user.company)
    technicians = User.objects.filter(company=user.company)
    return tickets, technicians


@login_required
def tickets_list_view(request):
    tickets_qs, _ = get_tickets_scope(request.user)

    if request.method == 'POST':
        if request.user.role == 'viewer':
            return HttpResponseForbidden("Você não tem permissão para abrir chamados.")
        form = TicketManualForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            if request.user.role == 'superadmin':
                if ticket.machine and ticket.machine.company != ticket.company:
                    form.add_error('machine', 'A máquina selecionada deve pertencer à empresa selecionada.')
            else:
                ticket.company = request.user.company
                if ticket.machine and ticket.machine.company != ticket.company:
                    form.add_error('machine', 'A máquina selecionada deve pertencer à sua empresa.')
            
            # Save if no errors were added
            if not form.errors:
                ticket.status = 'open'
                ticket.save()
                # Save foreign keys properly
                form.save_m2m()
                messages.success(request, f"Chamado #{ticket.id} aberto com sucesso.")
                return redirect('tickets_list')
    else:
        form = TicketManualForm(user=request.user)

    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')

    tickets = tickets_qs
    if status_filter in ['open', 'in_progress', 'resolved']:
        tickets = tickets.filter(status=status_filter)
    if priority_filter in ['low', 'medium', 'high', 'critical']:
        tickets = tickets.filter(priority=priority_filter)

    tickets = tickets.order_by('-created_at')

    return render(
        request,
        'tickets/list.html',
        {
            'tickets': tickets,
            'status_filter': status_filter,
            'priority_filter': priority_filter,
            'form': form,
        },
    )


@login_required
def ticket_detail_view(request, pk):
    tickets_qs, technicians = get_tickets_scope(request.user)
    ticket = get_object_or_404(
        tickets_qs.select_related('alert', 'alert__machine', 'assigned_to', 'company'),
        pk=pk,
    )

    if request.method == 'POST':
        if request.user.role == 'viewer':
            return HttpResponseForbidden("Você não tem permissão para alterar chamados.")

        action = request.POST.get('action')

        def render_timer_partial():
            return render(
                request,
                'tickets/partials/timer_section.html',
                {
                    'ticket': ticket,
                    'work_logs': ticket.work_logs.select_related('user').all(),
                    'active_work_log': ticket.work_logs.select_related('user').filter(is_active=True).first(),
                    'total_work_seconds': ticket.total_work_seconds,
                    'total_work_time_display': TicketReportService._format_duration(ticket.total_work_seconds),
                },
            )

        def get_timer_response():
            if request.META.get('HTTP_HX_REQUEST'):
                return render_timer_partial()
            return redirect('ticket_detail', pk=ticket.pk)

        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in ['open', 'in_progress', 'resolved']:
                ticket.status = new_status
                if new_status == 'resolved':
                    ticket.resolved_at = timezone.now()
                else:
                    ticket.resolved_at = None
                ticket.save(update_fields=['status', 'resolved_at'])
                messages.success(request, 'Status do chamado atualizado.')

        elif action == 'assign_tech':
            tech_id = request.POST.get('assigned_to')
            if tech_id:
                tech = get_object_or_404(technicians, pk=tech_id)
                ticket.assigned_to = tech
            else:
                ticket.assigned_to = None
            ticket.save(update_fields=['assigned_to'])
            messages.success(request, 'Técnico atribuído com sucesso.')

        elif action == 'timer_play':
            active_log = TicketWorkLog.objects.filter(ticket=ticket, is_active=True).select_related('user').first()
            if active_log and active_log.user_id != request.user.id:
                messages.error(request, 'Já existe um apontamento em andamento para este chamado.')
                return get_timer_response()

            if active_log and active_log.user_id == request.user.id:
                messages.info(request, 'Você já está com o timer ativo neste chamado.')
                return get_timer_response()

            note = (request.POST.get('note') or '').strip()
            TicketWorkLog.objects.create(
                ticket=ticket,
                user=request.user,
                note=note,
                is_active=True,
            )
            if ticket.status == 'open':
                ticket.status = 'in_progress'
                ticket.save(update_fields=['status'])
            messages.success(request, 'Timer iniciado com sucesso.')

        elif action == 'timer_pause':
            active_log = TicketWorkLog.objects.filter(ticket=ticket, is_active=True).select_related('user').first()
            if not active_log:
                messages.warning(request, 'Não existe timer ativo para pausar.')
                return get_timer_response()

            if active_log.user_id != request.user.id and request.user.role not in ['admin', 'superadmin']:
                return HttpResponseForbidden("Você não pode pausar o apontamento de outro técnico.")

            note = (request.POST.get('note') or '').strip()
            if note:
                if active_log.note:
                    active_log.note = f"{active_log.note}\n\n{note}"
                else:
                    active_log.note = note
                active_log.save(update_fields=['note'])
            active_log.pause()
            messages.success(request, 'Timer pausado e apontamento salvo.')

        elif action == 'save_work_note':
            note = (request.POST.get('note') or '').strip()
            if not note:
                messages.warning(request, 'Escreva um apontamento antes de salvar.')
                return get_timer_response()

            active_log = TicketWorkLog.objects.filter(ticket=ticket, is_active=True, user=request.user).first()
            if active_log:
                if active_log.note:
                    active_log.note = f"{active_log.note}\n\n{note}"
                else:
                    active_log.note = note
                active_log.save(update_fields=['note'])
            else:
                TicketWorkLog.objects.create(
                    ticket=ticket,
                    user=request.user,
                    note=note,
                    is_active=False,
                    duration_seconds=0,
                )
            messages.success(request, 'Apontamento salvo com sucesso.')

        elif action == 'generate_ai_report':
            try:
                TicketReportService.generate_report(ticket)
                messages.success(request, 'Relatório de IA gerado com sucesso.')
            except Exception as exc:
                messages.error(request, f'Não foi possível gerar o relatório de IA: {exc}')

        if action in ['timer_play', 'timer_pause', 'save_work_note']:
            return get_timer_response()
        return redirect('ticket_detail', pk=ticket.pk)

    return render(
        request,
        'tickets/detail.html',
        {
            'ticket': ticket,
            'technicians': technicians,
            'work_logs': ticket.work_logs.select_related('user').all(),
            'active_work_log': ticket.work_logs.select_related('user').filter(is_active=True).first(),
            'total_work_seconds': ticket.total_work_seconds,
            'total_work_time_display': TicketReportService._format_duration(ticket.total_work_seconds),
        },
    )
