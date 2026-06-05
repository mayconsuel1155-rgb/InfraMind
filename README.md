# InfraMind

InfraMind e uma plataforma SaaS multi-tenant para monitoramento de infraestrutura, alertas e chamados automáticos.

## O que o sistema faz hoje

- Cadastro de empresas e usuários por tenant
- Login por e-mail com funções de admin, technician, viewer e superadmin
- Isolamento completo e automático de dados por Tenant via `TenantManager`
- Registro de máquinas com chave de API individual
- Coleta detalhada de especificações físicas de hardware (módulos de RAM com velocidade/fabricante e discos físicos detalhados via WMI no agente Windows)
- Limites de alerta configuráveis (CPU, RAM, Disco) individualmente por tenant
- Heartbeat, métricas em tempo real de CPU, RAM e disco
- Inventário de softwares instalados
- Status de antivírus e firewall em tempo real
- Detecção heurística de risco:
  - ferramentas de acesso remoto
  - softwares potencialmente invasivos
  - processos suspeitos como PowerShell codificado e ferramentas de execução remota
- Alertas e abertura automática de chamados baseados nas métricas e regras de segurança
- Apontamento técnico de chamados (work logs) com timer de início/pausa e notas dinâmicas utilizando HTMX (sem reload)
- Configuração de IA por empresa para diagnósticos assistidos
- **Adequação e Conformidade LGPD:**
  - Termos de Consentimento (Opt-in) e Políticas de Privacidade obrigatórias no primeiro acesso com bloqueio via middleware.
  - Portabilidade de dados pessoais (exportação do perfil e históricos em JSON estruturado).
  - Direito de Esquecimento (anonimização irreversível de contas técnicas, preservando métricas e histórico de forma anônima).
  - Redefinição de senha segura por administradores do mesmo tenant.
  - Registro de todas as operações de tratamento de dados pessoais via tabela de auditoria `LGPDAuditLog`.

Importante: a detecção de risco é heurística. Ela ajuda muito no monitoramento, mas não substitui um EDR/IDS completo e não garante detectar todas as técnicas de invasão.

## Arquitetura rapida

- `backend/`: Django + DRF + PostgreSQL
- `agent/`: coletor Python instalado nas maquinas monitoradas
- `docker-compose.yml`: ambiente local com banco e backend

## Instalação e Execução do Servidor

Para uma instrução detalhada e completa de implantação, consulte o [MANUAL_CONFIGURACAO.md](file:///d:/InfraMind/MANUAL_CONFIGURACAO.md).

### Método A: Configuração Automatizada via Scripts (Recomendado)

1. **Configuração inicial:**
   Execute o script [instalar_servidor.bat](file:///d:/InfraMind/instalar_servidor.bat) como Administrador. Ele configurará automaticamente o ambiente Python virtual (`venv`), gerará chaves criptográficas exclusivas e guiará você na criação do Superusuário.
   
2. **Iniciar o sistema:**
   Execute o script [iniciar_sistema.bat](file:///d:/InfraMind/iniciar_sistema.bat) e escolha se deseja executar via Docker ou de forma nativa/manual rápida.

---

### Método B: Configuração Manual

#### Com Docker

1. Instale Docker e Docker Compose.
2. Na raiz do projeto, rode:

```bash
docker compose up --build
```

3. Acesse o backend em `http://localhost:8000`.

#### Sem Docker

1. Crie e ative um ambiente virtual.
2. Instale as dependências do backend.
3. Rode as migrations.
4. Crie um superusuário.
5. Inicie o servidor Django.

Exemplo:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Fluxo SaaS

1. O superadmin cria uma empresa.
2. O admin da empresa cria usuarios e registra maquinas.
3. Cada maquina recebe uma `api_key` unica.
4. O agente envia metricas, inventario e sinais de risco.
5. O backend gera alertas e tickets por empresa.

## Multi-login

O sistema usa sessoes normais do Django e nao faz bloqueio de sessao unica. Isso permite multiplos logins simultaneos, o que e o comportamento esperado para um SaaS com varios usuarios.

## Rotina do operador

- Verificar empresas ativas
- Criar usuarios por papel
- Registrar maquinas
- Conferir alertas criticos
- Validar tickets automaticos
- Manter a chave de IA por empresa

## Onde fica o agente

Veja o guia completo em [`agent/README.md`](agent/README.md).

