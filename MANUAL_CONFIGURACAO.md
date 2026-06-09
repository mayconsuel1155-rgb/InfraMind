# InfraMind — Manual de Configuração e Implantação (Instrução de Trabalho)

Este manual descreve o processo passo a passo para instalar, configurar e hospedar o servidor backend do **InfraMind**, bem como empacotar e implantar o agente de monitoramento nas estações de trabalho de colaboradores externos ou locais, garantindo a associação automática por tenant e o sincronismo dinâmico de dados (mesmo via VPN ou conexões externas).

---

## 1. Visão Geral da Arquitetura e Tenancy

O **InfraMind** é uma plataforma SaaS multi-tenant. Cada cliente representa uma Empresa (Tenant) isolada, que pode operar de forma independente ou sob uma estrutura hierárquica de **Matriz e Filiais**.
1. O **Administrador Geral** (Superadmin) ou o **Administrador do Tenant** (Admin da Matriz) cadastra a empresa (ou filial) no painel do InfraMind.
2. O sistema gera automaticamente um **Token de Registro** único para esta empresa/filial.
3. O **Agente** é instalado no computador do colaborador usando o Token de Registro específico daquela unidade e o endereço de rede do servidor.
4. O servidor reconhece o token, registra a máquina sob a empresa correta, gera uma `api_key` única e a devolve ao agente.
5. A partir desse instante, a máquina está vinculada e envia métricas continuamente.
6. Caso a estação de trabalho fique sem acesso à internet ou desconectada da VPN, o agente armazena os dados em um **buffer local offline** (`offline_metrics.json`) e os envia automaticamente em lote (bulk) no exato instante em que a conexão for restabelecida.

---

## 2. Requisitos Mínimos do Sistema

* **Servidor Backend**:
  * Windows Server 2019+ ou Linux (Ubuntu 20.04+)
  * Python 3.11 ou superior instalado (adicionado ao PATH do sistema)
  * Banco de Dados PostgreSQL 15+ ou SQLite para testes locais
  * Docker e Docker Compose (opcional)

* **Estações de Trabalho (Clientes)**:
  * Windows 10 ou 11 (recomendado para suporte completo à API WMI de hardware)
  * Conexão de rede ativa com o endereço do servidor (Internet pública ou VPN corporativa)

---

## 3. Instalação e Hospedagem do Servidor Backend

Você pode configurar e hospedar o backend de duas formas no Windows Server/Máquina Servidora:

### Opção A: Instalação Automatizada (Recomendado)

Utilize os scripts criados na raiz do projeto para automatizar a configuração:

1. **Instalar Dependências e Configurar**:
   Execute o script **[instalar_servidor.bat](file:///d:/InfraMind/instalar_servidor.bat)** com privilégios de Administrador. Ele fará o seguinte de forma 100% automática:
   * Criará o ambiente virtual Python (`venv`).
   * Atualizará o gerenciador de pacotes (`pip`).
   * Instalará todos os requisitos do sistema.
   * Criará o arquivo de configuração `backend/.env`.
   * **Gará chaves criptográficas de segurança únicas** (`SECRET_KEY` e `FIELD_ENCRYPTION_KEY` para criptografia de chaves de IA de forma segura).
   * Executará as migrações estruturais do banco de dados.
   * Oferecerá a criação guiada do Superusuário administrador do sistema.

2. **Iniciar o Servidor**:
   Execute o script **[iniciar_sistema.bat](file:///d:/InfraMind/iniciar_sistema.bat)**. Escolha uma das opções:
   * **Opção 1**: Executar com Docker (se possuir o Docker Desktop instalado). Sobe um banco Postgres robusto.
   * **Opção 2**: Executar de forma manual/nativa rápida (usa a `venv` e o banco SQLite embutido).

---

### Opção B: Instalação Manual Passo a Passo

Caso prefira configurar as etapas uma a uma:

1. Acesse a pasta do backend e crie o ambiente virtual:
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Instale as dependências requeridas:
   ```powershell
   pip install -r requirements/development.txt
   ```
3. Crie o arquivo `.env` na pasta `backend/` a partir do exemplo:
   ```powershell
   copy .env.example .env
   ```
4. Configure as variáveis fundamentais no seu `.env`:
   * `SECRET_KEY`: Uma chave de hash longa e secreta para segurança da sessão.
   * `FIELD_ENCRYPTION_KEY`: Uma chave Fernet de 32 bytes codificada em base64 (gerada com `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())`).
   * Configurações de banco de dados (`SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD`, `SQL_HOST`, `SQL_PORT`) caso vá apontar para um PostgreSQL em produção.
5. Execute as migrações e crie o superusuário administrador:
   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```
6. Inicie o servidor:
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```

> [!IMPORTANT]
> **Configurações de Rede Local e Firewall**:
> 1. **ALLOWED_HOSTS**: No arquivo `.env` do servidor, certifique-se de configurar `ALLOWED_HOSTS=*` (ou incluir o IP local do servidor, ex: `192.168.0.63`) para que o Django aceite conexões vindas de outras máquinas na rede.
> 2. **Liberação no Firewall**: Se o servidor estiver rodando no Windows, o sistema operacional bloqueará as conexões de rede local na porta `8000` por padrão. Para liberar a porta, abra o PowerShell como **Administrador** no servidor e execute:
>    ```powershell
>    New-NetFirewallRule -DisplayName "InfraMind Port 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
>    ```

> [!TIP]
> **Exposição Pública do Servidor**: Para monitorar colaboradores remotamente (home office), o servidor backend precisa ser acessível externamente. Você pode:
> * Configurar o servidor em uma nuvem (Render, Railway, AWS, Azure, GCP).
> * Configurar um IP público estático com redirecionamento de portas (port forwarding) no firewall/roteador da sua empresa apontando para a porta `8000`.
> * Configurar um DNS dinâmico (no-ip, DuckDNS) apontando para o roteador empresarial.
> * Exigir que as máquinas dos colaboradores acessem a **VPN da empresa**. A VPN cria um túnel e torna o endereço IP local do servidor (ex: `192.168.1.100`) perfeitamente visível para os computadores dos colaboradores externos enquanto a VPN estiver ativa.

---

## 4. O Agente de Monitoramento (Instalação e Vinculação Automática)

O código-fonte do agente está localizado na pasta **[agent](file:///d:/InfraMind/agent/)**.

### Como gerar o Executável (`.exe`) para Distribuição
Para gerar o executável final que será instalado nas estações dos funcionários:
1. Abra um terminal do PowerShell na máquina de compilação (Windows) e acesse a pasta do agente:
   ```powershell
   cd agent
   ```
2. Crie e ative um ambiente virtual temporário para instalar as dependências de build:
   ```powershell
   py -3 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install pyinstaller
   ```
3. Gere o executável autônomo com o PyInstaller:
   ```powershell
   pyinstaller --onefile --noconsole main.py
   ```
   * *Nota*: O parâmetro `--noconsole` impede a abertura de uma janela preta de terminal, rodando o agente de forma oculta em background.

### Script de Instalação e Execução Automatizada (`instalar_agente.bat`)
Para máquinas de teste ou desenvolvimento que executam o código Python diretamente (sem compilar para executável), você pode utilizar o script **[instalar_agente.bat](file:///d:/InfraMind/agent/instalar_agente.bat)**:
1. Copie a pasta `agent` inteira para a máquina.
2. Execute o bat. Ele irá:
   * Verificar a presença do Python.
   * Criar a pasta virtual `.venv` local e instalar automaticamente todas as dependências do `requirements.txt`.
   * Iniciar o agente em modo interativo.
3. **Instalação Silenciosa**: Você também pode rodar o bat por linha de comando passando os parâmetros da empresa:
   ```cmd
   instalar_agente.bat "http://seu-servidor-ip-ou-dns:8000" "TOKEN_REGISTRO_DA_EMPRESA"
   ```
   Isso instalará as dependências e registrará a máquina silenciosamente no backend.

---

### Métodos de Instalação e Registro Automático (Tenancy)

O agente possui suporte a registros **100% silenciosos (sem interface gráfica ou prompts)** para facilitar a automação.

#### Método 1: Por Linha de Comando (GPO / Scripts Batch ou PowerShell)
Você pode executar o agente passando parâmetros no terminal. Ele se registrará no backend silenciosamente, criará a máquina vinculada à empresa correta e iniciará a coleta em segundo plano:
```powershell
inframind-agent.exe --backend "http://seu-servidor-ip-ou-dns:8000" --token "TOKEN_REGISTRO_DA_EMPRESA"
```

#### Método 2: Por Arquivo de Configuração Prévia (`config.json`)
Você pode empacotar ou colocar na mesma pasta do executável do agente um arquivo chamado `config.json` contendo a URL e o token de registro da empresa específica:
```json
{
    "backend_url": "http://seu-servidor-ip-ou-dns:8000",
    "registration_token": "TOKEN_REGISTRO_DA_EMPRESA"
}
```
Ao ser iniciado sem argumentos de terminal, o agente lerá o `config.json`, identificará o token, registrará a máquina silenciosamente no backend, gerará a `api_key` exclusiva da estação de trabalho e reescreverá o `config.json` contendo apenas as chaves autorizadas finais:
```json
{
    "backend_url": "http://seu-servidor-ip-ou-dns:8000",
    "api_key": "uuid-unico-gerado-pelo-servidor",
    "hostname": "DESKTOP-COLABORADOR",
    "company": "Nome da Empresa no Sistema"
}
```

#### Método 3: Registro Interativo (Para testes manuais)
Ao executar o agente sem argumentos e sem um arquivo `config.json` na mesma pasta, ele exibirá um assistente interativo no terminal perguntando a URL do servidor e o token de registro da empresa de forma amigável.

---

### Inteligência e Auto-Recuperação do Agente (Self-healing)

O agente possui duas lógicas internas para evitar erros comuns de duplicação ou chaves inválidas:
1. **Detecção de Nova Estação (Cópia de Pasta)**: Se a pasta do agente contendo um `config.json` configurado for copiada para outra máquina, o agente detectará que o hostname do sistema operacional não bate com o registrado no JSON. Ele então limpa as chaves antigas e força o cadastro automático desta nova máquina com o seu nome correto.
2. **Auto-Recuperação de Chave Rejeitada**: Se o servidor backend rejeitar a chave de API do agente (ex: caso o banco do servidor seja resetado ou a máquina seja excluída), o agente identifica a rejeição (erro de autenticação), remove o `config.json` inválido e reinicia o assistente de registro interativo na tela.

---

### Inicialização Automática no Windows (Startup)

Para garantir que o agente sempre inicie junto com o Windows das estações monitoradas:
1. **Pasta Inicializar (Startup)**: Copie o arquivo `inframind-agent.exe` ou um atalho dele para a pasta de inicialização comum de todos os usuários:
   `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp`
2. **Agendador de Tarefas do Windows**: Crie uma tarefa agendada para rodar ao iniciar o sistema:
   ```powershell
   schtasks /create /tn "InfraMindAgent" /tr "C:\Caminho\inframind-agent.exe" /sc onstart /ru "SYSTEM"
   ```
   *(Executar sob a conta SYSTEM garante que o agente continue monitorando mesmo que nenhum usuário esteja logado).*

---

### Como identificar se o Agente está ativo na máquina?

Você pode verificar se o monitoramento está rodando ativamente na estação de trabalho de quatro maneiras:

1. **Pelo Painel do InfraMind (Dashboard)**:
   * Acesse a tela de Máquinas no painel do administrador. O status da máquina cadastrada deve constar como **Online** (marcado com um ícone verde) e o horário do campo *Última Vez Visto* (`last_seen`) deve estar se atualizando a cada 60 segundos.

2. **Pelo Gerenciador de Tarefas do Windows (Task Manager)**:
   * **Se compilado (.exe)**: Pressione `Ctrl + Shift + Esc` e procure na aba "Processos" ou "Detalhes" pelo nome do seu executável (ex: `inframind-agent.exe` ou `main.exe`).
   * **Se rodando via Python**: Procure na aba "Processos" por `python.exe` ou `pythonw.exe`.

3. **Pela Linha de Comando (CMD ou PowerShell)**:
   Execute o seguinte comando para listar se o processo está em execução:
   * No CMD:
     ```cmd
     tasklist /fi "imagename eq inframind-agent.exe"
     ```
   * No PowerShell:
     ```powershell
     Get-Process -Name "inframind-agent" -ErrorAction SilentlyContinue
     ```

4. **Pelo console ou arquivo de logs**:
   * Se o agente estiver executando com o console aberto, você verá mensagens periódicas impressas como: `[+] Heartbeat sent successfully.` e `[+] Metrics sent -> CPU: X%, RAM: Y%`.
   * Se houver queda de internet, o agente imprimirá mensagens de aviso informando que as métricas foram retidas localmente em buffer.

---

## 5. Funcionamento Offline e Conectividade via VPN/Rede Interna

O agente do InfraMind gerencia problemas de conectividade de maneira inteligente:
* **Quando o usuário está fora da empresa (sem internet ou fora da VPN)**: O agente não consegue falar com o backend. Ele continuará registrando o uso de CPU, RAM, disco e ameaças de segurança localmente em um arquivo chamado `offline_metrics.json` na pasta do agente.
* **Quando o usuário se conecta à VPN corporativa ou retorna para o escritório**: O agente detectará a conexão ativa no próximo ciclo de batimento (heartbeat). Ele fará a transição automática de estado para **Online**, coletará o histórico do arquivo `offline_metrics.json` e enviará todos os dados acumulados ao servidor em uma única requisição em massa (bulk), limpando o cache local.

Dessa forma, o histórico de uso e alertas nunca se perde e a auditoria permanece completa.

---

## 6. Gestão Avançada de Tenancy: Matriz e Filiais

Para atender cenários corporativos complexos, o **InfraMind** suporta uma estrutura hierárquica de empresas (**Matriz e Filiais**), permitindo controle consolidado ao mesmo tempo que mantém o isolamento estrito de dados para inquilinos individuais.

### 6.1. O que é a Hierarquia de Empresas?

* **Empresa Matriz**: É uma empresa raiz que não possui nenhuma controladora vinculada. Administradores da matriz possuem visibilidade agregada sobre os seus próprios recursos e sobre todas as filiais a ela associadas.
* **Empresa Filial**: É uma empresa cadastrada que aponta para uma empresa Matriz por meio do campo `parent_company` (Matriz). O isolamento de dados de telemetria é feito no nível da filial, mas a visualização é propagada para cima na hierarquia.

### 6.2. Permissões de Criação e Edição de Empresas

A gestão de empresas e a configuração de hierarquias variam de acordo com a função do usuário:

* **Administrador Geral (Superadmin)**:
  * Pode criar e editar qualquer empresa no sistema.
  * Pode vincular qualquer empresa a qualquer outra como matriz/filial (campo `parent_company` livre no formulário).
  * Tem visibilidade de todas as máquinas, alertas, usuários e logs do sistema global.
* **Administrador do Tenant (Admin)**:
  * Pode editar os dados cadastrais da sua própria empresa (CNPJ, Razão Social, Nome Fantasia, Telefone, E-mail, Endereço completo).
  * Pode criar novas **Filiais** sob a sua própria empresa. O formulário de criação oculta o campo `parent_company` e o preenche automaticamente com o ID de sua própria empresa, impedindo a criação de filiais vinculadas a outras matrizes.
  * Pode editar os dados cadastrais de filiais criadas sob a sua matriz.
  * *Nota*: Usuários com permissão de Técnico ou Visualizador não possuem acesso ao console de gerenciamento de empresas.

### 6.3. Comportamento do Isolamento no Banco de Dados (`TenantQuerySet`)

O isolamento multi-tenant é implementado de forma transparente na camada do banco de dados (através do `TenantQuerySet`), garantindo segurança sem sobrecarregar a lógica de desenvolvimento:

* **Para a Filial**: Usuários vinculados a uma filial enxergam apenas as máquinas, alertas, chamados e dados gerados especificamente para aquela filial.
* **Para a Matriz**: Usuários vinculados à matriz visualizam de forma consolidada todos os dados de telemetria, chamados abertos e alertas da matriz e de **todas as suas filiais**.
* **Como funciona tecnicamente**:
  * Ao carregar a lista de recursos, o sistema faz uma verificação condicional na query:
    ```python
    # Se for uma empresa (Company): retorna ela mesma + filiais associadas
    return self.filter(Q(pk=tenant.pk) | Q(parent_company=tenant))
    
    # Se for um recurso (como Máquina, Alerta, Ticket):
    return self.filter(Q(company=tenant) | Q(company__parent_company=tenant))
    ```

### 6.4. Passos para Cadastrar e Associar uma Filial

1. **Acessar a Console de Gestão**: Um administrador (Superadmin ou Admin da Matriz) deve navegar até o painel `/management/`.
2. **Preencher o Formulário**: No painel de criação de empresas, preencha os dados cadastrais (Razão Social, CNPJ, E-mail, Endereço, etc.).
   * Se você for **Superadmin**, selecione a empresa matriz correspondente no campo `Matriz (Caso esta seja uma filial)`.
   * Se você for um **Admin de Empresa**, a nova empresa criada será configurada automaticamente como uma filial da sua empresa atual.
3. **Obter o Token**: Após a criação, anote o **Token de Registro** gerado especificamente para a filial.

### 6.5. Instalação do Agente e Envio de Telemetria em Filiais

* Cada filial possui seu próprio **Token de Registro** exclusivo.
* **Importante**: Nunca instale o agente em uma filial usando o token da matriz, caso contrário todas as métricas daquela máquina serão computadas diretamente na matriz. Use sempre o token gerado para la filial específica.
* Após a primeira inicialização do agente com o token da filial, o servidor cria a máquina vinculada àquela filial, gera uma chave `api_key` exclusiva e mantém o fluxo de envio periódico de métricas. O administrador da matriz verá a máquina listada sob a filial correspondente no painel consolidado.

---

## 7. Módulo de Relatórios de Manutenção e Ordens de Serviço (O.S.)

O InfraMind inclui um sistema completo para registro de manutenções preventivas, corretivas e upgrades realizados nas estações de trabalho.

### 7.1. Funcionalidades do Módulo de Manutenção
* **Registro Técnico Detalhado**: Permite informar descrição do problema, serviço realizado, tipo (Preventiva, Corretiva, Limpeza, Upgrade HW/SW), prazos e dias de garantia.
* **Gestão de Custos e Peças**: É possível listar individualmente as peças utilizadas no reparo (ex: SSD, Memória RAM) e o custo de mão de obra. O sistema calcula o valor total automaticamente.
* **Integração com Tenancy e Máquinas**: Cada relatório fica vinculado ao equipamento e à respectiva empresa/filial do cliente.
* **Ordem de Serviço (PDF)**: O sistema gera um documento limpo e profissional otimizado para impressão (A4) contendo os dados do serviço e linhas para assinatura do cliente e do técnico.

### 7.2. Como utilizar
1. Acesse a seção **Manutenção** no menu lateral do painel.
2. Clique em **Nova Manutenção**.
3. Preencha os dados e adicione as peças em **Itens e Peças**.
4. Salve e clique no botão **Imprimir Relatório** para gerar o comprovante final para o cliente.
