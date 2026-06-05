# InfraMind — Documento Mestre
> Versão 2.0 — Revisado e expandido

---

## Visão Geral

O InfraMind é uma plataforma SaaS para monitoramento e gestão de infraestrutura de TI.

O sistema possui:

- Inventário automático de máquinas
- Monitoramento em tempo real (CPU, RAM, disco)
- Alertas inteligentes com níveis de severidade
- Chamados automáticos baseados em alertas
- Diagnóstico assistido por IA (configurável)

Foco principal:

- Simplicidade e MVP rápido
- Baixo custo operacional
- Escalabilidade progressiva
- Automação do trabalho repetitivo

---

## Glossário

| Termo | Definição |
|---|---|
| **Agente** | Programa Python instalado na máquina do cliente, responsável por coletar e enviar dados |
| **Heartbeat** | Sinal periódico enviado pelo agente para confirmar que a máquina está online |
| **Engine de Regras** | Módulo do backend que analisa métricas recebidas e decide se deve gerar alertas |
| **Tenant** | Empresa cliente cadastrada na plataforma. Cada tenant vê apenas seus próprios dados |
| **Métrica** | Snapshot de uso de CPU, RAM ou disco em um determinado momento |
| **Chamado (Ticket)** | Registro de ocorrência criado automaticamente ou manualmente a partir de um alerta |

---

## Objetivo do MVP

Criar uma solução capaz de:

1. Registrar máquinas automaticamente via agente
2. Monitorar CPU, RAM e disco continuamente
3. Detectar problemas críticos via engine de regras
4. Gerar alertas automáticos classificados por severidade
5. Abrir chamados automaticamente a partir de alertas críticos
6. Exibir tudo em um dashboard web simples e funcional

> **Critério de MVP concluído:** Um técnico consegue instalar o agente em uma máquina Windows, ver essa máquina no dashboard, receber um alerta de CPU alta e encontrar um chamado aberto automaticamente — sem nenhuma configuração manual no backend.

---

## Arquitetura Geral

```text
Máquina Windows
  └── Agente Python (psutil + requests)
        ↓ HTTPS + API Key
API Django REST
  └── Engine de Regras
        ↓
PostgreSQL
  └── Dashboard Web (Django Templates + Bootstrap)
```

---

## Multi-tenancy

Cada empresa cliente é um **tenant isolado**:

- Usuários pertencem a uma empresa
- Máquinas pertencem a uma empresa
- Alertas e tickets são visíveis apenas para a empresa dona
- Existe um papel `superadmin` (interno da InfraMind) com acesso global para suporte

### Papéis de usuário

| Papel | Permissões |
|---|---|
| `superadmin` | Acesso total a todos os tenants |
| `admin` | Gerencia usuários, máquinas e configurações da sua empresa |
| `technician` | Visualiza e atualiza chamados, vê alertas |
| `viewer` | Somente leitura no dashboard |

---

## Autenticação

### Dashboard (usuários humanos)
- Login com e-mail e senha
- Sessão via JWT (access token + refresh token)
- Token armazenado no localStorage do browser

### Agente (máquinas)
- Cada máquina recebe uma **API Key** única no momento do registro
- Todas as chamadas do agente usam `Authorization: ApiKey <chave>` no header
- API Keys podem ser revogadas individualmente pelo admin

---

## Stack Oficial

### Backend
- Python 3.11+
- Django 4.x
- Django REST Framework
- PostgreSQL 15+
- Simple JWT

### Frontend
- Django Templates
- Bootstrap 5
- HTMX (interações dinâmicas e reativas sem reload de página)
- Chart.js (gráficos simples)

### Agente
- Python 3.10+
- psutil
- requests
- wmi (somente Windows)
- pyinstaller (para gerar o `.exe`)

### Hospedagem
- Render ou Railway (backend + banco)

---

## Configuração de IA no Frontend

O InfraMind usa IA para diagnóstico assistido e sugestões automáticas. Para permitir flexibilidade e não criar dependência de um único provedor, **a chave de API de IA é configurada pelo próprio usuário admin no painel**.

### Como funciona

1. O admin acessa **Configurações → Integrações → IA**
2. Escolhe o provedor desejado
3. Insere a chave de API
4. A chave é salva criptografada no banco (por tenant)
5. O backend usa a chave configurada em todas as chamadas de IA daquele tenant

### Provedores suportados (MVP e futuro)

| Provedor | Modelos suportados | Status |
|---|---|---|
| Anthropic | claude-sonnet-4, claude-haiku-4 | ✅ MVP |
| OpenAI | gpt-4o, gpt-4o-mini | ✅ MVP |
| Google | gemini-1.5-pro, gemini-flash | 🔜 Fase 5 |
| Ollama (local) | llama3, mistral, etc. | 🔜 Fase 5 |

### Model no banco

```python
class AIConfig(models.Model):
    company = models.OneToOneField('companies.Company', on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)          # 'anthropic', 'openai', etc.
    model_name = models.CharField(max_length=100)        # 'claude-sonnet-4', 'gpt-4o', etc.
    api_key_encrypted = models.TextField()               # chave criptografada com Fernet
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Interface de configuração (tela)

```
Configurações → Integrações → IA
┌─────────────────────────────────────────┐
│ Provedor de IA                          │
│ [Anthropic ▼]                           │
│                                         │
│ Modelo                                  │
│ [claude-sonnet-4 ▼]                     │
│                                         │
│ Chave de API                            │
│ [sk-ant-••••••••••••••••]  [Testar]     │
│                                         │
│ [Salvar configuração]                   │
└─────────────────────────────────────────┘
```

### Serviço unificado de IA (backend)

```python
# core/services/ai_service.py

class AIService:
    """Abstração que roteia chamadas para o provedor configurado pelo tenant."""

    def __init__(self, company):
        self.config = AIConfig.objects.get(company=company, is_active=True)

    def complete(self, prompt: str) -> str:
        if self.config.provider == 'anthropic':
            return self._call_anthropic(prompt)
        elif self.config.provider == 'openai':
            return self._call_openai(prompt)
        else:
            raise ValueError(f"Provedor não suportado: {self.config.provider}")
```

---

## Estrutura do Projeto

```text
infra-mind/
│
├── backend/
├── agent/
├── frontend/
├── docs/
└── scripts/
```

### Estrutura Backend

```text
backend/
│
├── apps/
│   ├── accounts/       # usuários, autenticação, papéis
│   ├── companies/      # tenants, configurações por empresa
│   ├── agents/         # registro, API Keys, heartbeat
│   ├── inventory/      # máquinas, softwares instalados
│   ├── monitoring/     # métricas de CPU/RAM/disco
│   ├── alerts/         # engine de regras, alertas
│   ├── tickets/        # chamados automáticos e manuais
│   └── integrations/   # configuração de IA e outros provedores
│
├── core/
│   ├── services/
│   │   └── ai_service.py
│   └── encryption.py
│
└── requirements/
    ├── base.txt
    ├── development.txt
    └── production.txt
```

### Estrutura do Agente

```text
agent/
│
├── core/
│   ├── inventory.py    # coleta hostname, IP, SO, hardware, softwares
│   ├── monitor.py      # coleta CPU, RAM, disco periodicamente
│   └── security.py     # verifica antivírus, firewall
│
├── services/
│   ├── api_client.py   # comunicação HTTPS com o backend
│   └── scheduler.py    # agenda tarefas periódicas
│
├── main.py
└── config.json         # endpoint da API + API Key da máquina
```

---

## Modelos Principais

### Company (Tenant)
```python
class Company(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.FileField(upload_to='company_logos/', null=True, blank=True)
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True)
    trade_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # Address details
    address_zip_code = models.CharField(max_length=9, null=True, blank=True)
    address_street = models.CharField(max_length=200, null=True, blank=True)
    address_number = models.CharField(max_length=20, null=True, blank=True)
    address_complement = models.CharField(max_length=100, null=True, blank=True)
    address_neighborhood = models.CharField(max_length=100, null=True, blank=True)
    address_city = models.CharField(max_length=100, null=True, blank=True)
    address_state = models.CharField(max_length=2, null=True, blank=True)
    
    registration_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### User
```python
class User(AbstractBaseUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    role = models.CharField(choices=ROLE_CHOICES, max_length=20)
    is_active = models.BooleanField(default=True)
```

### Machine
```python
class Machine(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='machines')
    hostname = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    operating_system = models.CharField(max_length=200)
    cpu_model = models.CharField(max_length=200)
    cpu_cores = models.IntegerField()
    ram_total_gb = models.FloatField()
    disk_total_gb = models.FloatField()
    api_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(choices=STATUS_CHOICES, max_length=20, default='offline')
    last_seen = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    ram_details = models.TextField(blank=True, default='', verbose_name="Detalhes da Memória")
    disk_details = models.TextField(blank=True, default='', verbose_name="Detalhes do Disco")
```

### Metric
```python
class Metric(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='metrics')
    cpu_percent = models.FloatField()
    ram_percent = models.FloatField()
    disk_percent = models.FloatField()
    collected_at = models.DateTimeField()
```

### Alert
```python
class Alert(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='alerts')
    severity = models.CharField(choices=[('low', 'Baixo'), ('high', 'Alto'), ('critical', 'Crítico')], max_length=20)
    type = models.CharField(max_length=100)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
```

### Ticket
```python
class Ticket(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='tickets')
    alert = models.ForeignKey(Alert, null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets')
    machine = models.ForeignKey('agents.Machine', null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets')
    title = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(choices=[('open', 'Aberto'), ('in_progress', 'Em Andamento'), ('resolved', 'Resolvido')], max_length=20, default='open')
    priority = models.CharField(choices=[('low', 'Baixa'), ('medium', 'Média'), ('high', 'Alta'), ('critical', 'Crítica')], max_length=20, default='medium')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    ai_report = models.TextField(blank=True)
    ai_report_generated_at = models.DateTimeField(null=True, blank=True)

    @property
    def total_work_seconds(self):
        # Calcula total de segundos de trabalho somando os apontamentos (work logs)
```

### TicketWorkLog (Apontamentos de Chamado)
```python
class TicketWorkLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='work_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_work_logs')
    note = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def pause(self):
        # Pausa o timer e calcula a duração da sessão
```

### InstalledSoftware
```python
class InstalledSoftware(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='softwares')
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=100, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    installed_at = models.DateTimeField(auto_now=True)
```

### SecurityStatus
```python
class SecurityStatus(models.Model):
    machine = models.OneToOneField(Machine, on_delete=models.CASCADE, related_name='security_status')
    antivirus_active = models.BooleanField(default=True)
    firewall_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### MonitoringThreshold
```python
class MonitoringThreshold(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='monitoring_threshold')
    cpu_limit = models.FloatField(default=95.0)
    ram_limit = models.FloatField(default=90.0)
    disk_limit = models.FloatField(default=80.0)
```

---

## APIs Principais

### Agente → Backend

```
POST /api/agent/register          # Primeira execução: registra a máquina
POST /api/agent/heartbeat         # A cada 1 min: confirma que está online
POST /api/agent/inventory         # A cada 24h: atualiza inventário completo
POST /api/agent/metrics           # A cada 5 min: envia CPU, RAM, disco
```

### Exemplos de payload

**POST /api/agent/metrics**
```json
{
  "api_key": "uuid-da-maquina",
  "collected_at": "2025-01-15T14:30:00Z",
  "cpu_percent": 87.5,
  "ram_percent": 92.1,
  "disk_percent": 65.0
}
```

**POST /api/agent/register**
```json
{
  "hostname": "DESKTOP-ABC123",
  "ip_address": "192.168.1.100",
  "operating_system": "Windows 11 Pro 23H2",
  "cpu_model": "Intel Core i7-10700",
  "cpu_cores": 8,
  "ram_total_gb": 16.0,
  "disk_total_gb": 512.0,
  "registration_token": "token-gerado-no-dashboard"
}
```

### Dashboard → Backend

```
GET  /api/dashboard               # Resumo geral (contadores)
GET  /api/machines                # Lista de máquinas
GET  /api/machines/{id}           # Detalhe de uma máquina + últimas métricas
GET  /api/alerts                  # Lista de alertas (com filtros)
GET  /api/tickets                 # Lista de chamados
PATCH /api/tickets/{id}           # Atualiza status do chamado
```

---

## Engine de Regras

O backend avalia cada métrica recebida contra as regras. Os limites de métricas de hardware (`disk_percent`, `ram_percent`, `cpu_percent`) podem ser customizados por empresa através do modelo `MonitoringThreshold`. Os valores padrão do sistema são indicados abaixo:

### Alertas por métrica

| Condição | Severidade | Tipo |
|---|---|---|
| `disk_percent > disk_limit` (Padrão: `80%`) | `low` | `disk_warning` |
| `ram_percent > ram_limit` (Padrão: `90%`) | `high` | `ram_high` |
| `cpu_percent > cpu_limit` (Padrão: `95%`) | `high` | `cpu_high` |
| Nenhum heartbeat por 5 min | `critical` | `machine_offline` |
| Disco com falha (SMART) | `critical` | `disk_failure` |
| Antivírus desabilitado | `critical` | `antivirus_disabled` |
| Firewall desabilitado | `high` | `firewall_disabled` |

### Regras de supressão

- Não criar alerta duplicado se já existe um alerta ativo do mesmo tipo para a mesma máquina
- Resolver automaticamente o alerta quando a condição voltar ao normal

### Abertura automática de tickets

- Alertas com severidade `critical` abrem um chamado automaticamente
- Alertas `high` abrem chamado se persistirem por mais de 15 minutos
- Alertas `low` apenas notificam no dashboard

---

## Deploy do Agente

Para o MVP, o agente é distribuído como executável Windows:

1. Admin gera um **token de registro** no dashboard (válido por 24h)
2. Admin faz download do `inframind-agent.exe`
3. Instala na máquina do cliente
4. Na primeira execução, informa o token e o endpoint da API
5. O agente se registra, recebe sua API Key e começa a operar como serviço Windows

---

## Dashboard — Telas

### Login
- E-mail e senha
- Redirect para dashboard após autenticação

### Dashboard (home)
- Total de máquinas online / offline
- Alertas críticos ativos
- Chamados abertos
- Gráfico de saúde geral (últimas 24h)

### Máquinas
- Lista com hostname, IP, status, última vez visto
- Detalhe: histórico de métricas, alertas recentes

### Alertas
- Filtros por severidade (crítico / alto / baixo)
- Filtro por máquina
- Botão para marcar como resolvido manualmente

### Chamados
- Abertos / Em andamento / Concluídos
- Atribuição a técnico
- Atualização de status

### Configurações → Integrações → IA
- Provedor, modelo e API Key configuráveis por empresa

---

## Roadmap

### Fase 1 — Base
- [x] Estrutura do projeto Django
- [x] Models: Company, User, Machine
- [x] Autenticação JWT + API Key
- [x] API de registro do agente

### Fase 2 — Monitoramento
- [x] API de métricas e heartbeat
- [x] Engine de regras básica
- [x] Dashboard com dados reais

### Fase 3 — Automação
- [x] Alertas automáticos
- [x] Tickets automáticos
- [x] Supressão de duplicatas

### Fase 4 — Interface
- [x] Gráficos com Chart.js
- [x] Layout responsivo
- [x] Tela de configuração de IA

### Fase 5 — IA
- [x] Diagnóstico automático de alertas
- [x] Sugestões de resolução
- [x] Resumo semanal de saúde
- [x] Suporte a múltiplos provedores (Google, Ollama)

### Fase 6 — Automações e Relatórios SaaS (Adicional de UI/UX)
- [x] Busca automática e preenchimento de cadastro de empresas por CNPJ via BrasilAPI
- [x] Upload de Logotipo corporativo por tenant (customização de marca no relatório)
- [x] Mapeamento de status e de severidade coloridos no dashboard e folhas impressas
- [x] Abertura manual de chamados com filtragem dinâmica por tenant para técnicos e superadmins
- [x] Relatório técnico de IA estruturado sob modelo ABNT com estilização avançada (suporte a blocos de código/terminal)
- [x] Validação obrigatória de apontamentos técnicos antes da emissão de relatórios de IA

### Fase 7 — Segurança, Tenancy, HTMX e Hardware Detalhado
- [x] Isolamento completo de dados por Tenant via `TenantManager` global
- [x] UX reativa com HTMX (apontamentos dinâmicos, timer síncrono e OOB swaps)
- [x] Coleta detalhada de hardware do agente Windows (módulos de RAM e Discos físicos via WMI)
- [x] Compatibilidade com Python 3.14 para suíte de testes unitários
- [x] Limites de alertas customizáveis (`MonitoringThreshold`) por empresa/tenant

### Fase 8 — Adequação LGPD e Gestão de Usuários
- [x] Termos de Consentimento (Opt-in) e Política de Privacidade obrigatórios para usuários autenticados
- [x] Middleware `LGPDConsentMiddleware` de interceptação e bloqueio de acessos não-consentidos
- [x] Exportação de dados pessoais para portabilidade em formato JSON estruturado
- [x] Anonimização completa da conta técnica (Direito de Esquecimento), preservando a integridade relacional de logs e chamados
- [x] Redefinição segura e isolada por tenant de senhas dos usuários
- [x] Tabela de Logs de Auditoria de Tratamento de Dados Pessoais `LGPDAuditLog` com visibilidade por tenant

---

## Regras de Desenvolvimento

### Sempre
- Priorizar simplicidade
- Evitar overengineering
- Criar código modular e funções pequenas
- Usar nomes claros e autodescritivos
- Documentar todas as APIs
- Focar no funcionamento do MVP antes de polir

### Não fazer agora
- Microserviços ou Kubernetes
- Frontend em React
- App mobile
- Antivírus próprio
- IA avançada sem configuração básica funcionando

---

## Visão Futura

O InfraMind deve evoluir para:

- Monitoramento inteligente e preditivo
- Automação operacional completa
- Análise de tendências e anomalias
- Suporte assistido por IA com múltiplos provedores
- Plataforma SaaS escalável com planos por número de máquinas
