from django.utils import timezone
from apps.tickets.models import Ticket
from apps.integrations.services import AIService

class TicketAutomationService:
    """
    Automates creation, suppression, and resolution workflows of support tickets from system alerts.
    """
    @classmethod
    def create_ticket_from_alert(cls, alert):
        # 1. Check for existing active ticket for the same alert to prevent duplication (suppression)
        existing_ticket = Ticket.objects.filter(
            alert=alert,
            status__in=['open', 'in_progress']
        ).first()
        if existing_ticket:
            return existing_ticket

        # 2. Check for active tickets of same alert type on the same machine (broader suppression)
        broad_existing_ticket = Ticket.objects.filter(
            alert__machine=alert.machine,
            alert__type=alert.type,
            status__in=['open', 'in_progress']
        ).first()
        if broad_existing_ticket:
            return broad_existing_ticket

        # 3. Map severity to priority
        priority_map = {
            'critical': 'critical',
            'high': 'high',
            'low': 'low'
        }
        priority = priority_map.get(alert.severity, 'medium')

        # 4. Generate title and description
        title = f"Incidente: {alert.type.upper()} em {alert.machine.hostname}"
        description = (
            f"Chamado gerado automaticamente pela Engine de Automação do InfraMind.\n\n"
            f"Detalhes do Alerta:\n"
            f"- Máquina: {alert.machine.hostname} (IP: {alert.machine.ip_address})\n"
            f"- Tipo: {alert.type}\n"
            f"- Severidade: {alert.get_severity_display()}\n"
            f"- Ocorrência: {alert.created_at.strftime('%d/%m/%Y H:%M:%S')}\n"
            f"- Descrição: {alert.message}\n"
        )

        # 5. Create Ticket
        ticket = Ticket.objects.create(
            company=alert.machine.company,
            alert=alert,
            title=title,
            description=description,
            priority=priority,
            status='open'
        )
        return ticket


class TicketReportService:
    """
    Builds and persists AI-generated operational reports for tickets.
    """

    @staticmethod
    def _format_duration(total_seconds: int) -> str:
        total_seconds = max(0, int(total_seconds or 0))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

    @classmethod
    def build_context(cls, ticket):
        work_logs = ticket.work_logs.select_related('user').all()
        logs_text = []
        for log in work_logs:
            status = "em andamento" if log.is_active else f"pausado em {log.paused_at.strftime('%d/%m/%Y %H:%M') if log.paused_at else 'N/A'}"
            logs_text.append(
                "- Técnico: {user}\n"
                "  Início: {start}\n"
                "  Situação: {status}\n"
                "  Horas: {hours}\n"
                "  Apontamento: {note}".format(
                    user=log.user.email,
                    start=log.started_at.strftime('%d/%m/%Y %H:%M'),
                    status=status,
                    hours=cls._format_duration(log.duration_seconds if not log.is_active else log.duration_seconds + int((timezone.now() - log.started_at).total_seconds())),
                    note=log.note.strip() or "Sem apontamento",
                )
            )

        alert_block = "Sem alerta associado."
        if ticket.alert:
            alert = ticket.alert
            alert_block = (
                f"- Tipo: {alert.type}\n"
                f"- Severidade: {alert.get_severity_display()}\n"
                f"- Status: {'Resolvido' if alert.is_resolved else 'Ativo'}\n"
                f"- Mensagem: {alert.message}\n"
                f"- Máquina: {alert.machine.hostname} ({alert.machine.ip_address})\n"
                f"- Ocorrência: {alert.created_at.strftime('%d/%m/%Y %H:%M')}"
            )

        return {
            "ticket": ticket,
            "alert_block": alert_block,
            "work_logs": "\n\n".join(logs_text) if logs_text else "Nenhum apontamento registrado.",
            "total_work_time": cls._format_duration(ticket.total_work_seconds),
        }

    @classmethod
    def generate_report(cls, ticket):
        # Validate that there are technician notes (apontamentos) registered
        has_notes = False
        for log in ticket.work_logs.all():
            if log.note and log.note.strip():
                has_notes = True
                break

        if not has_notes:
            raise ValueError(
                "Não é possível gerar o relatório sem apontamentos técnicos detalhados. "
                "Por favor, registre pelo menos um apontamento descrevendo as ações tomadas e o status da resolução."
            )

        ai_service = AIService(ticket.company)
        context = cls.build_context(ticket)

        import datetime
        now_str = datetime.datetime.now().strftime("%d/%m/%Y")
        assigned_name = ticket.assigned_to.email if ticket.assigned_to else "Não designado"
        city = ticket.company.address_city or "São Paulo"
        state = ticket.company.address_state or "SP"

        prompt = f"""
Você é um Engenheiro de Suporte e Especialista em Incidentes.

Gere um Relatório Técnico de Incidente formal, em português, em formato Markdown, estritamente em conformidade com as normas da ABNT (especialmente ABNT NBR 10719 para relatórios técnicos).

Estruture o documento exatamente com o seguinte formato e cabeçalho formal:

---
**PLATAFORMA INFRAMIND — MONITORAMENTO E RESPOSTA A INCIDENTES**
**RELATÓRIO TÉCNICO DE INCIDENTE: CHAMADO #{ticket.id}**

* **Título do Incidente:** {ticket.title}
* **Organização / Cliente:** {ticket.company.name}
* **Autor / Responsável:** {assigned_name}
* **Local de Execução:** {city} - {state}
* **Data do Relatório:** {now_str}
---

O corpo do relatório deve conter as seguintes seções numeradas:

## 1. INTRODUÇÃO
(Descreva de forma impessoal o objetivo do chamado, o dispositivo associado e o nível de criticidade do incidente. Use a descrição do chamado: "{ticket.description}")

## 2. DESCRIÇÃO DO INCIDENTE E EVIDÊNCIAS COLETADAS
(Descreva os alertas e evidências técnicas reportadas. Use os dados do alerta: {context['alert_block']})

## 3. ATIVIDADES DESENVOLVIDAS
(Apresente de forma cronológica as ações e notas tomadas pelos técnicos. Use os apontamentos: {context['work_logs']})

## 4. ANÁLISE TÉCNICA E HIPÓTESE DE CAUSA RAIZ
(Valide e analise todos os apontamentos de suporte realizados pelos técnicos na Seção 3. Com base neles, estabeleça com clareza a causa raiz técnica do problema)

## 5. CONCLUSÕES E STATUS DA RESOLUÇÃO
(Apresente as conclusões do incidente. Determine formal e explicitamente, baseando-se estritamente nos apontamentos técnicos da Seção 3, se o problema do cliente foi resolvido com sucesso ou se ainda permanece aberto/pendente. Indique o tempo total de trabalho [{context['total_work_time']}] e proponha recomendações ou próximas etapas preventivas)

**REGRAS DE REDAÇÃO:**
- Use voz passiva e linguagem formal/impessoal (ex: "identificou-se" em vez de "eu identifiquei").
- Não inclua notas introdutórias ou explicações externas; responda diretamente em Markdown formatado.
""".strip()

        report = ai_service.generate_completion(prompt)
        if report.startswith("Erro:"):
            raise ValueError(report)
        ticket.ai_report = report
        ticket.ai_report_generated_at = timezone.now()
        ticket.save(update_fields=['ai_report', 'ai_report_generated_at'])
        return report
