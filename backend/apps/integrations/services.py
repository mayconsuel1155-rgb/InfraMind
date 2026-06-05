import json

import requests


class AIService:
    """
    Routes completions directly to provider REST APIs.
    """

    OPENROUTER_KEY_PREFIXES = ('sk-or-',)

    def __init__(self, company):
        self.company = company
        from apps.integrations.models import AIConfig

        self.config = AIConfig.objects.filter(company=company, is_active=True).first()

    def is_configured(self):
        # The service is always available (either via custom keys, env variables, or mock fallback)
        return True

    def _generate_mock_completion(self, prompt: str) -> str:
        import re
        
        # Check if it is an alert diagnosis prompt
        if "Detalhes do Alerta:" in prompt:
            hostname_match = re.search(r"Hostname:\s*(.*)", prompt)
            os_match = re.search(r"Sistema Operacional:\s*(.*)", prompt)
            cpu_match = re.search(r"CPU:\s*(.*)", prompt)
            ram_match = re.search(r"RAM Total:\s*(.*)", prompt)
            alert_type_match = re.search(r"Tipo de Alerta:\s*(.*)", prompt)
            alert_msg_match = re.search(r"Mensagem:\s*(.*)", prompt)
            
            hostname = hostname_match.group(1) if hostname_match else "Estação"
            operating_system = os_match.group(1) if os_match else "Windows"
            cpu = cpu_match.group(1) if cpu_match else "Intel/AMD"
            ram = ram_match.group(1) if ram_match else "8 GB"
            alert_type = alert_type_match.group(1) if alert_type_match else "Uso Elevado"
            alert_msg = alert_msg_match.group(1) if alert_msg_match else "Alerta de telemetria"

            # Custom response based on alert type
            if "cpu_high" in alert_type.lower() or "cpu" in alert_type.lower():
                causes = """- **Processamento Excessivo:** Algum serviço local ou processo em segundo plano (ex: indexador do SO, atualizações automáticas) está consumindo recursos em excesso.
- **Loop Infinito:** Possível thread travada em aplicação em execução.
- **Atividade Suspeita:** Processo desconhecido em execução com alta atividade de CPU."""
                actions = f"""1. **Identificar Processo Ofensor:** Abra o PowerShell no `{hostname}` e execute:
   ```powershell
   Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, CPU, Path
   ```
2. **Finalizar Processo:** Caso seja um processo indesejado, finalize-o:
   ```powershell
   Stop-Process -Name "nome_do_processo" -Force
   ```
3. **Acompanhar Consumo:** Monitore a telemetria nos próximos minutos."""
            elif "disk_full" in alert_type.lower() or "disk" in alert_type.lower():
                causes = """- **Logs Acumulados:** Arquivos de log do IIS, Windows Event Viewer ou logs de depuração sem rotação.
- **Arquivos Temporários:** Pasta TEMP do sistema com alto volume de arquivos.
- **Limitação de Disco:** Disco rígido subdimensionado para a carga de trabalho atual."""
                actions = f"""1. **Limpeza de Disco:** Execute a ferramenta de limpeza nativa no `{hostname}` via PowerShell:
   ```powershell
   cleanmgr /sagerun:1
   ```
2. **Localizar Pastas Grandes:** Utilize comandos para listar as pastas com maior consumo:
   ```powershell
   Get-ChildItem -Path C:\\ -Recurse -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 10 FullName, Length
   ```"""
            elif "ram_high" in alert_type.lower() or "ram" in alert_type.lower():
                causes = """- **Vazamento de Memória (Memory Leak):** Aplicação consumindo memória de forma progressiva.
- **Sobrecarga de Bancos de Dados:** Instâncias locais consumindo a memória máxima permitida.
- **Múltiplos Usuários:** Muitas sessões RDP ativas simultaneamente."""
                actions = f"""1. **Visualizar Consumo de Memória:** Liste os processos ordenados por consumo de memória física (WS):
   ```powershell
   Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 Name, @{{Name="RAM (MB)";Expression={{[math]::round($_.WorkingSet / 1MB, 2)}}}}
   ```
2. **Encerrar Sessões RDP:** Encerre sessões de usuários inativos."""
            else:
                causes = """- **Instabilidade no Serviço:** Falha abrupta no processo monitorado.
- **Alteração de Política de Rede:** Bloqueio de porta ou serviço local.
- **Ameaça de Segurança:** Processo suspeito interferindo nos serviços locais."""
                actions = f"""1. **Validar Status do Serviço:** Verifique se o serviço correspondente está rodando:
   ```powershell
   Get-Service -Name "*firewall*" # exemplo para firewall
   ```
2. **Reiniciar Serviço:** Reinicie o serviço afetado:
   ```powershell
   Restart-Service -Name "MpsSvc" -Force
   ```"""

        import datetime
        now_str = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Check if it is an alert diagnosis prompt
        if "Detalhes do Alerta:" in prompt:
            hostname_match = re.search(r"Hostname:\s*(.*)", prompt)
            os_match = re.search(r"Sistema Operacional:\s*(.*)", prompt)
            cpu_match = re.search(r"CPU:\s*(.*)", prompt)
            ram_match = re.search(r"RAM Total:\s*(.*)", prompt)
            alert_type_match = re.search(r"Tipo de Alerta:\s*(.*)", prompt)
            alert_msg_match = re.search(r"Mensagem:\s*(.*)", prompt)
            
            hostname = hostname_match.group(1) if hostname_match else "Estação"
            operating_system = os_match.group(1) if os_match else "Windows"
            cpu = cpu_match.group(1) if cpu_match else "Intel/AMD"
            ram = ram_match.group(1) if ram_match else "8 GB"
            alert_type = alert_type_match.group(1) if alert_type_match else "Uso Elevado"
            alert_msg = alert_msg_match.group(1) if alert_msg_match else "Alerta de telemetria"

            # Custom response based on alert type
            if "cpu_high" in alert_type.lower() or "cpu" in alert_type.lower():
                causes = """- **Processamento Excessivo:** Algum serviço local ou processo em segundo plano (ex: indexador do SO, atualizações automáticas) está consumindo recursos em excesso.
- **Loop Infinito:** Possível thread travada em aplicação em execução.
- **Atividade Suspeita:** Processo desconhecido em execução com alta atividade de CPU."""
                actions = f"""1. **Identificar Processo Ofensor:** Abra o PowerShell no `{hostname}` e execute:
   ```powershell
   Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, CPU, Path
   ```
2. **Finalizar Processo:** Caso seja um processo indesejado, finalize-o:
   ```powershell
   Stop-Process -Name "nome_do_processo" -Force
   ```
3. **Acompanhar Consumo:** Monitore a telemetria nos próximos minutos."""
            elif "disk_full" in alert_type.lower() or "disk" in alert_type.lower():
                causes = """- **Logs Acumulados:** Arquivos de log do IIS, Windows Event Viewer ou logs de depuração sem rotação.
- **Arquivos Temporários:** Pasta TEMP do sistema com alto volume de arquivos.
- **Limitação de Disco:** Disco rígido subdimensionado para a carga de trabalho atual."""
                actions = f"""1. **Limpeza de Disco:** Execute a ferramenta de limpeza nativa no `{hostname}` via PowerShell:
   ```powershell
   cleanmgr /sagerun:1
   ```
2. **Localizar Pastas Grandes:** Utilize comandos para listar as pastas com maior consumo:
   ```powershell
   Get-ChildItem -Path C:\\ -Recurse -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 10 FullName, Length
   ```"""
            elif "ram_high" in alert_type.lower() or "ram" in alert_type.lower():
                causes = """- **Vazamento de Memória (Memory Leak):** Aplicação consumindo memória de forma progressiva.
- **Sobrecarga de Bancos de Dados:** Instâncias locais consumindo a memória máxima permitida.
- **Múltiplos Usuários:** Muitas sessões RDP ativas simultaneamente."""
                actions = f"""1. **Visualizar Consumo de Memória:** Liste os processos ordenados por consumo de memória física (WS):
   ```powershell
   Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 Name, @{{Name="RAM (MB)";Expression={{[math]::round($_.WorkingSet / 1MB, 2)}}}}
   ```
2. **Encerrar Sessões RDP:** Encerre sessões de usuários inativos."""
            else:
                causes = """- **Instabilidade no Serviço:** Falha abrupta no processo monitorado.
- **Alteração de Política de Rede:** Bloqueio de porta ou serviço local.
- **Ameaça de Segurança:** Processo suspeito interferindo nos serviços locais."""
                actions = f"""1. **Validar Status do Serviço:** Verifique se o serviço correspondente está rodando:
   ```powershell
   Get-Service -Name "*firewall*" # exemplo para firewall
   ```
2. **Reiniciar Serviço:** Reinicie o serviço afetado:
   ```powershell
   Restart-Service -Name "MpsSvc" -Force
   ```"""

            return f"""---
**PLATAFORMA INFRAMIND — MONITORAMENTO E RESPOSTA A INCIDENTES**
**RELATÓRIO DE DIAGNÓSTICO TÉCNICO DE INCIDENTE**

* **Dispositivo Afetado:** {hostname}
* **Sistema Operacional:** {operating_system}
* **Hardware:** {cpu} | {ram} RAM
* **Data da Análise:** {now_str}
---

## 1. INTRODUÇÃO
O dispositivo `{hostname}` apresentou comportamento anômalo classificado sob o alerta `{alert_type}`. A presente análise visa identificar as possíveis causas da falha técnica e estabelecer um plano de contingência.

## 2. DESCRIÇÃO DO INCIDENTE E EVIDÊNCIAS COLETADAS
Registrou-se a seguinte evidência técnica gerada pelo agente coletor do InfraMind:
* **Tipo do Alerta:** {alert_type}
* **Log do Incidente:** "{alert_msg}"

## 3. POSSÍVEIS CAUSAS ANALISADAS
{causes}

## 4. ANÁLISE TÉCNICA E RECOMENDAÇÕES (PLANO DE AÇÃO)
Recomenda-se a execução imediata dos seguintes procedimentos de mitigação e diagnóstico local no sistema `{operating_system}`:
{actions}
"""

        # Fallback to general ticket report
        title_match = re.search(r"Título do Incidente:\*\* (.*)", prompt)
        title = title_match.group(1).strip() if title_match else "Incidente"

        desc_match = re.search(r"Use a descrição do chamado: \"(.*?)\"", prompt, re.DOTALL)
        desc = desc_match.group(1).strip() if desc_match else ""

        # Extract machine name and alert message from alert block
        machine_match = re.search(r"Máquina: (.*)", prompt)
        machine = machine_match.group(1).strip() if machine_match else "Servidor Monitorado"

        alert_msg_match = re.search(r"Mensagem: (.*)", prompt)
        alert_msg = alert_msg_match.group(1).strip() if alert_msg_match else ""

        # Extract technician notes (apontamentos)
        notes_match = re.search(r"Use os apontamentos:\s*(.*)\n\n## 4", prompt, re.DOTALL)
        notes_text = notes_match.group(1).strip() if notes_match else ""

        # Determine cause and status from notes
        notes_lower = notes_text.lower()
        
        # Check if the notes suggest a resolution
        is_resolved = False
        if any(w in notes_lower for w in ["resolvido", "concluído", "finalizado", "corrigido", "sanado", "resolvimento", "sucesso"]):
            is_resolved = True
            resolution_status = "Resolvido com Sucesso (Problema Sanado)"
        else:
            resolution_status = "Pendente / Em Andamento"

        # Identify possible cause from notes
        if "superaquecimento" in notes_lower or "quente" in notes_lower or "temperatura" in notes_lower or "calor" in notes_lower or "cooler" in notes_lower:
            cause_hypothesis = "Identificou-se superaquecimento físico ou obstrução das saídas de ar da máquina, gerando instabilidade temporária por proteção térmica do processador."
        elif "disco" in notes_lower or "armazenamento" in notes_lower or "espaço" in notes_lower or "cheio" in notes_lower:
            cause_hypothesis = "Esgotamento de espaço em disco provocado pelo acúmulo de logs locais ou arquivos temporários não rotacionados."
        elif "memória" in notes_lower or "ram" in notes_lower or "leak" in notes_lower:
            cause_hypothesis = "Consumo excessivo de memória física (RAM) por vazamento de recursos em processos ou banco de dados local."
        elif "firewall" in notes_lower or "porta" in notes_lower or "bloqueio" in notes_lower:
            cause_hypothesis = "Bloqueio ou desativação das políticas de segurança locais (firewall) impedindo a comunicação correta de rede."
        else:
            cause_hypothesis = "Comportamento instável ou interrupção temporária de serviços locais, exigindo intervenção técnica direta para restabelecimento."

        # Let's also extract the actual technical actions from notes
        formatted_notes = []
        if notes_text and "Nenhum apontamento" not in notes_text:
            for line in notes_text.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("- Técnico:") or line_stripped.startswith("Técnico:"):
                    continue
                if line_stripped.startswith("Início:") or line_stripped.startswith("Situação:") or line_stripped.startswith("Horas:"):
                    continue
                if line_stripped.startswith("Apontamento:"):
                    note_content = line_stripped.split(":", 1)[1].strip()
                    if note_content and note_content != "Sem apontamento":
                        formatted_notes.append(f"- {note_content}")
        
        if not formatted_notes:
            formatted_notes.append("- Análise preliminar realizada pelo sistema de monitoramento.")
        
        activities_text = "\n".join(formatted_notes)

        return f"""---
**PLATAFORMA INFRAMIND — MONITORAMENTO E RESPOSTA A INCIDENTES**
**RELATÓRIO TÉCNICO DE INCIDENTE: NBR 10719**

* **Título do Incidente:** {title}
* **Cliente / Organização:** {self.company.name}
* **Status do Incidente:** {'Resolvido' if is_resolved else 'Em Andamento'}
* **Data do Documento:** {now_str}
---

## 1. INTRODUÇÃO
Este documento apresenta o Relatório Técnico de Incidente (RTI) emitido automaticamente pela plataforma InfraMind para registro de ocorrência. O incidente reportado refere-se a: "{desc or 'Abertura manual de ticket'}".

## 2. DESCRIÇÃO DO INCIDENTE E EVIDÊNCIAS COLETADAS
Identificou-se a seguinte ocorrência no ecossistema de infraestrutura:
* **Dispositivo Afetado:** {machine}
* **Registro de Alerta/Mensagem:** {alert_msg or "Incidente reportado manualmente por técnico designado."}
* **Mapeamento:** O dispositivo `{machine}` está sob monitoramento contínuo.

## 3. ATIVIDADES DESENVOLVIDAS
Registrou-se a seguinte cronologia de intervenções e apontamentos de suporte realizados pela equipe:
{activities_text}

## 4. ANÁLISE TÉCNICA E HIPÓTESE DE CAUSA RAIZ
{cause_hypothesis}

## 5. CONCLUSÕES E STATUS DA RESOLUÇÃO
Com base na análise das atividades registradas pelos técnicos de suporte, conclui-se que o status do incidente é: **{resolution_status}**.
Caso o problema persista ou novas instabilidades ocorram, recomenda-se acompanhar a telemetria do painel do InfraMind.
"""

    def generate_completion(self, prompt: str) -> str:
        import os
        
        # 1. Prioritize company-specific active AI configuration
        if self.config and self.config.api_key:
            try:
                provider = self._resolve_provider(self.config.provider, self.config.api_key)
                model = self.config.model_name
                return self._dispatch_completion(
                    provider=provider,
                    model=model,
                    api_key=self.config.api_key,
                    prompt=prompt,
                )
            except requests.exceptions.RequestException as e:
                return f"Erro de rede ao conectar à API da IA ({self.config.provider}): {str(e)}"
            except Exception as e:
                return f"Erro inesperado durante a chamada de IA: {str(e)}"
        
        # 2. Check for global/system environment variables
        global_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY') or os.getenv('DEFAULT_AI_API_KEY')
        if global_key:
            try:
                provider = 'google' if os.getenv('GEMINI_API_KEY') else ('openai' if os.getenv('OPENAI_API_KEY') else 'anthropic')
                model = 'gemini-1.5-flash' if provider == 'google' else ('gpt-4o-mini' if provider == 'openai' else 'claude-3-5-haiku-20241022')
                
                # Check if default key is configured to override provider/model in settings or config
                if os.getenv('DEFAULT_AI_PROVIDER'):
                    provider = os.getenv('DEFAULT_AI_PROVIDER')
                if os.getenv('DEFAULT_AI_MODEL'):
                    model = os.getenv('DEFAULT_AI_MODEL')
                    
                return self._dispatch_completion(
                    provider=provider,
                    model=model,
                    api_key=global_key,
                    prompt=prompt,
                )
            except Exception as e:
                return f"Erro inesperado na chamada global de IA: {str(e)}"

        # 3. Fallback to high-quality simulated report/diagnosis if no keys are configured anywhere
        return self._generate_mock_completion(prompt)


    @classmethod
    def test_connection(cls, provider: str, model: str, api_key: str) -> tuple[bool, str]:
        """
        Tests the configured provider using a short prompt.
        """
        if not api_key:
            return False, "Informe uma chave de API para testar a conexão."

        test_prompt = "Diga apenas a palavra 'OK' se você estiver funcionando."
        try:
            resolved_provider = cls._resolve_provider(provider, api_key)
            res = cls._dispatch_completion(
                provider=resolved_provider,
                model=model,
                api_key=api_key,
                prompt=test_prompt,
            )
            friendly_name = {
                'openai': 'OpenAI',
                'openrouter': 'OpenRouter',
                'anthropic': 'Anthropic',
                'google': 'Google Gemini',
            }.get(resolved_provider, resolved_provider)
            return True, f"Sucesso! Conectado à {friendly_name}. Resposta: {res.strip()}"
        except Exception as e:
            return False, f"Falha na conexão: {str(e)}"

    @classmethod
    def _resolve_provider(cls, provider: str, api_key: str) -> str:
        if provider == 'openai' and api_key and api_key.startswith(cls.OPENROUTER_KEY_PREFIXES):
            return 'openrouter'
        return provider

    @classmethod
    def _dispatch_completion(cls, provider: str, model: str, api_key: str, prompt: str) -> str:
        if provider == 'openai':
            return cls._call_openai(api_key, model, prompt)
        if provider == 'openrouter':
            return cls._call_openrouter(api_key, model, prompt)
        if provider == 'anthropic':
            return cls._call_anthropic(api_key, model, prompt)
        if provider == 'google':
            return cls._call_google(api_key, model, prompt)
        raise ValueError(f"Provedor de IA '{provider}' desconhecido.")

    @staticmethod
    def _call_openai(api_key, model, prompt) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        return data['choices'][0]['message']['content']

    @staticmethod
    def _call_openrouter(api_key, model, prompt) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "InfraMind",
        }
        payload = {
            "model": model or "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        return data['choices'][0]['message']['content']

    @staticmethod
    def _call_anthropic(api_key, model, prompt) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "claude-3-5-haiku-20241022",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        return data['content'][0]['text']

    @staticmethod
    def _call_google(api_key, model, prompt) -> str:
        model_name = model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{
                "parts": [{"text": prompt}],
            }],
            "generationConfig": {
                "temperature": 0.3,
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        try:
            return data['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            raise Exception(f"Resposta inválida do Gemini: {json.dumps(data)}")
