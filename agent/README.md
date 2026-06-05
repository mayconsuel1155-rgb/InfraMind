# InfraMind Agent

Este agente e o componente instalado nas maquinas dos clientes ou colaboradores. Ele coleta informacoes do sistema, envia metricas periodicas e reporta sinais heuristicos de risco.

## Funcionalidades

- Registro automático na empresa via token
- Heartbeat periódico
- Coleta detalhada de especificações físicas de hardware (módulos de RAM com fabricante, velocidade e tamanho individual, além do modelo e tamanho de cada disco físico conectado usando WMI)
- Envio de CPU, RAM e disco (métricas de utilização em tempo real)
- Envio de status de antivírus e firewall (segurança de endpoint)
- Inventário de softwares instalados
- Buffer offline para envio posterior (guarda métricas localmente em `offline_metrics.json` se o servidor estiver inacessível)
- Detecção heurística de risco:
  - softwares de acesso remoto
  - ferramentas potencialmente invasivas
  - processos suspeitos como PowerShell codificado

## Limites importantes

O agente nao e um EDR/IDS completo. Ele nao detecta todas as formas possiveis de invasao e deve ser usado como camada de observabilidade e resposta, junto com boas politicas de rede, endpoint protection e auditoria.

## Requisitos

- Windows 10/11 recomendado para a coleta completa
- Python 3.10 ou superior
- Acesso ao backend do InfraMind

Dependencias principais:

- `requests`
- `psutil`
- `wmi` no Windows

## Instalacao

### Opção A: Execução via Python (Desenvolvimento/Testes)

1. Copie a pasta `agent/` para a máquina alvo.
2. Crie e ative um ambiente virtual:

```bash
cd agent
py -3 -m venv .venv
.venv\Scripts\activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Execute o agente:

```bash
python main.py
```

5. O agente iniciará em modo interativo caso não encontre argumentos ou um `config.json` pré-existente. Informe:
   - URL do backend (ex: `http://localhost:8000`)
   - Token de registro da empresa

Depois disso, o agente se registra no backend, recebe uma `api_key` única, salva as configurações no `config.json` local e passa a rodar.

Como alternativa de automação local, você também pode usar o script [instalar_agente.bat](file:///d:/InfraMind/agent/instalar_agente.bat).

---

### Opção B: Implantação de Produção via Executável (.exe)

Para simplificar a distribuição em computadores de colaboradores, você pode gerar um executável autônomo.

#### 1. Empacotamento
Instale o PyInstaller e gere o executável de modo oculto (sem janela de terminal):

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole main.py
```

*Nota:* O parâmetro `--noconsole` impede que a janela preta de console apareça para o usuário final, mantendo o processo invisível em background.

#### 2. Métodos de Registro e Associação por Empresa (Tenancy)
O agente possui suporte a registros **100% silenciosos (sem prompts ou interação)**:

* **Método 1: Por Linha de Comando (GPO / Scripts):**
  Execute o executável passando a URL e o token de registro gerado no painel da empresa:
  ```powershell
  inframind-agent.exe --backend "http://seu-servidor-ip-ou-dns:8000" --token "TOKEN_REGISTRO_DA_EMPRESA"
  ```

* **Método 2: Por Arquivo de Configuração Prévia (`config.json`):**
  Coloque na mesma pasta do executável do agente um arquivo chamado `config.json` contendo:
  ```json
  {
      "backend_url": "http://seu-servidor-ip-ou-dns:8000",
      "registration_token": "TOKEN_REGISTRO_DA_EMPRESA"
  }
  ```
  Ao iniciar sem parâmetros, o agente lerá o `config.json`, registrará a máquina silenciosamente no backend, gerará a `api_key` exclusiva e reescreverá o arquivo de forma limpa e autenticada.

---

### 3. Configuração de Inicialização Automática (Startup)

Para garantir que o agente sempre inicie junto com o Windows das estações monitoradas:

* **Opção 1: Pasta Inicializar (Startup)**
  Copie o arquivo `inframind-agent.exe` (ou um atalho dele) para a pasta de inicialização comum de todos os usuários:
  `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp`

* **Opção 2: Agendador de Tarefas do Windows (Recomendado)**
  Crie uma tarefa agendada para rodar ao iniciar o sistema usando privilégios da conta `SYSTEM` (garante a execução mesmo se nenhum usuário estiver logado):
  ```powershell
  schtasks /create /tn "InfraMindAgent" /tr "C:\Caminho\inframind-agent.exe" /sc onstart /ru "SYSTEM"
  ```

---

## Fluxo de uso

1. O admin cria a empresa no painel.
2. O admin pega o token de registro da empresa.
3. O agente é executado na máquina do cliente usando um dos métodos de instalação.
4. O backend retorna a `api_key` da máquina.
5. O agente passa a enviar telemetria automaticamente.

---

## Operacao e Resiliência Offline

- **Heartbeat:** a cada 60 segundos
- **Métricas:** a cada 15 segundos
- **Inventário de softwares:** na inicialização e depois a cada 24 horas

**Funcionamento Offline:**
Caso a máquina perca conexão com a internet ou se desconecte da VPN corporativa, o agente continuará registrando o uso de CPU, RAM, disco e ameaças de segurança localmente no arquivo `offline_metrics.json`. Assim que a conexão for restabelecida, os dados acumulados serão enviados automaticamente em lote (bulk) ao backend, limpando o cache local.

## Inteligência de Auto-Recuperação e Boas Práticas

- **Prevenção de Duplicidades (Cópia de Pasta)**: Se a pasta do agente contendo um `config.json` ativo for copiada para outro computador, o agente detectará que o hostname do Windows é diferente do configurado no JSON. Ele removerá a chave de API antiga e os dados do outro computador automaticamente, iniciando um novo cadastro com o nome correto.
- **Auto-recuperação (Self-healing)**: Caso o servidor backend rejeite a chave de API (ex: se o banco de dados for recriado), o agente identificará a falha de autenticação, excluirá o `config.json` e abrirá o assistente de registro interativo no terminal.
- Cada máquina precisa de sua própria `api_key` exclusiva.
- Ajuste o `backend_url` no arquivo de configuração conforme o ambiente (ex: o IP local do seu servidor `http://192.168.0.63:8000` se estiver na mesma rede local/Wi-Fi/VPN, ou o endereço DNS público do servidor).
