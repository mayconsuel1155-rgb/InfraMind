import platform
import subprocess
import json
import psutil

SOFTWARE_THREAT_RULES = [
    {
        "id": "remote_access_tool",
        "severity": "high",
        "title": "Ferramenta de acesso remoto detectada",
        "keywords": [
            "anydesk",
            "teamviewer",
            "rustdesk",
            "ultravnc",
            "tightvnc",
            "radmin",
            "screenconnect",
            "logmein",
        ],
        "message": "Ferramenta de acesso remoto encontrada no inventario. Verifique se o uso foi autorizado.",
    },
    {
        "id": "potential_intrusion_tool",
        "severity": "critical",
        "title": "Ferramenta potencialmente invasiva detectada",
        "keywords": [
            "mimikatz",
            "metasploit",
            "meterpreter",
            "powersploit",
            "empire",
            "cobalt strike",
            "psexec",
            "wmiexec",
            "nmap",
            "masscan",
            "hydra",
        ],
        "message": "Software com assinatura potencialmente invasiva foi detectado.",
    },
]

PROCESS_THREAT_RULES = [
    {
        "id": "encoded_powershell",
        "severity": "critical",
        "title": "PowerShell codificado em execução",
        "name_keywords": ["powershell.exe", "pwsh.exe"],
        "cmd_keywords": ["-enc", "-encodedcommand"],
        "message": "Processo PowerShell com comando codificado detectado. Isso pode indicar execução maliciosa.",
    },
    {
        "id": "credential_dumping_tool",
        "severity": "critical",
        "title": "Ferramenta de dump de credenciais detectada",
        "name_keywords": ["mimikatz", "procdump", "lsass"],
        "cmd_keywords": ["mimikatz", "procdump", "lsass"],
        "message": "Processo associado a dump de credenciais detectado. Investigue imediatamente.",
    },
    {
        "id": "remote_exec_tool",
        "severity": "high",
        "title": "Ferramenta de execucao remota detectada",
        "name_keywords": ["psexec", "wmic", "csexec", "winrs"],
        "cmd_keywords": ["psexec", "wmic", "winrs"],
        "message": "Processo de execucao remota detectado. Verifique a legitimidade do uso.",
    },
]


def _normalize_text(value):
    return " ".join((value or "").lower().split())

def get_installed_software():
    if platform.system() != "Windows":
        return []

    import winreg
    apps = []
    paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for hive, path in paths:
        try:
            key = winreg.OpenKey(hive, path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub_key_name = winreg.EnumKey(key, i)
                    sub_key = winreg.OpenKey(key, sub_key_name)
                    
                    try:
                        name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                    except Exception:
                        name = None

                    if not name or not name.strip():
                        continue

                    try:
                        version, _ = winreg.QueryValueEx(sub_key, "DisplayVersion")
                    except Exception:
                        version = "N/A"
                    try:
                        publisher, _ = winreg.QueryValueEx(sub_key, "Publisher")
                    except Exception:
                        publisher = "N/A"
                        
                    apps.append({
                        "name": name.strip(),
                        "version": version.strip() if version else "N/A",
                        "publisher": publisher.strip() if publisher else "N/A"
                    })
                except Exception:
                    pass
        except Exception:
            pass

    # De-duplicate by name
    seen = set()
    unique_apps = []
    for app in apps:
        if app["name"] not in seen:
            seen.add(app["name"])
            unique_apps.append(app)
    
    # Sort alphabetically
    unique_apps.sort(key=lambda x: x["name"].lower())
    return unique_apps


def get_installed_software_threats(softwares):
    threats = []
    seen = set()

    for software in softwares or []:
        name = _normalize_text(software.get("name"))
        if not name:
            continue

        for rule in SOFTWARE_THREAT_RULES:
            if rule["id"] in seen:
                continue
            if any(keyword in name for keyword in rule["keywords"]):
                seen.add(rule["id"])
                threats.append({
                    "type": f"security_{rule['id']}",
                    "severity": rule["severity"],
                    "title": rule["title"],
                    "message": f"{rule['message']} Encontrado: {software.get('name', 'desconhecido')}.",
                    "source": "inventory",
                })

    return threats


def get_runtime_security_threats():
    threats = []
    seen = set()

    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            proc_name = _normalize_text(proc.info.get('name'))
            cmdline = _normalize_text(" ".join(proc.info.get('cmdline') or []))

            for rule in PROCESS_THREAT_RULES:
                if rule["id"] in seen:
                    continue

                name_match = any(keyword in proc_name for keyword in rule["name_keywords"])
                cmd_match = any(keyword in cmdline for keyword in rule["cmd_keywords"])
                if name_match and cmd_match:
                    seen.add(rule["id"])
                    threats.append({
                        "type": f"security_{rule['id']}",
                        "severity": rule["severity"],
                        "title": rule["title"],
                        "message": f"{rule['message']} Processo: {proc.info.get('name', 'desconhecido')}.",
                        "source": "process",
                    })
    except Exception:
        pass

    return threats

def get_security_status():
    status = {
        "antivirus_active": True,
        "firewall_active": True
    }

    if platform.system() != "Windows":
        # Default active for non-windows platforms for MVP
        return status

    # Check Firewall status
    try:
        # Query firewall profiles state using powershell
        fw_check = subprocess.run(
            ["powershell", "-Command", "(Get-NetFirewallProfile -Profile Domain,Private,Public).Enabled"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if fw_check.returncode == 0:
            outputs = fw_check.stdout.strip().split('\n')
            # If all profiles are False, firewall is inactive
            status["firewall_active"] = any(val.strip() == "True" for val in outputs if val.strip())
        else:
            raise Exception("Powershell failed")
    except Exception:
        # Fallback to query service status
        try:
            svc_check = subprocess.run(["sc", "query", "MpsSvc"], capture_output=True, text=True, timeout=5)
            status["firewall_active"] = "RUNNING" in svc_check.stdout
        except Exception:
            pass

    # Check Antivirus status
    try:
        import wmi
        w = wmi.WMI(namespace="root/SecurityCenter2")
        av_products = w.AntivirusProduct()
        if av_products:
            # Check if at least one antivirus is active
            status["antivirus_active"] = False
            for av in av_products:
                state = av.productState
                # WMI state: if active, typically the 4th hex digit from end is 1, e.g. state & 0x1000 != 0
                is_active = (state & 0x1000) != 0
                if is_active:
                    status["antivirus_active"] = True
                    break
        else:
            status["antivirus_active"] = False
    except Exception:
        # Fallback to query Windows Defender via powershell
        try:
            defender_check = subprocess.run(
                ["powershell", "-Command", "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if defender_check.returncode == 0 and defender_check.stdout.strip():
                status["antivirus_active"] = defender_check.stdout.strip() == "True"
            else:
                # Sc query WinDefend
                svc_av = subprocess.run(["sc", "query", "WinDefend"], capture_output=True, text=True, timeout=5)
                status["antivirus_active"] = "RUNNING" in svc_av.stdout
        except Exception:
            pass

    return status


def get_network_security_threats():
    threats = []
    # 4444: Metasploit, 6667: IRC, 31337: Back Orifice
    SUSPICIOUS_PORTS = {4444, 6667, 31337}
    try:
        connections = psutil.net_connections(kind='tcp')
        for conn in connections:
            if conn.raddr and conn.raddr.port in SUSPICIOUS_PORTS:
                proc_name = "desconhecido"
                if conn.pid:
                    try:
                        proc_name = psutil.Process(conn.pid).name()
                    except Exception:
                        pass
                
                threats.append({
                    "type": "security_suspicious_network_connection",
                    "severity": "critical",
                    "title": "Conexão de rede suspeita detectada",
                    "message": (
                        f"Processo '{proc_name}' estabeleceu uma conexão TCP com a porta remota "
                        f"{conn.raddr.port} ({conn.raddr.ip}). Isso pode indicar atividade de canal C2 (Comando e Controle)."
                    ),
                    "source": "network",
                })
    except Exception:
        pass
    return threats
