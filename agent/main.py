import os
import sys
import json
import socket
import platform
import time
from pathlib import Path

import psutil

# Add local path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.api_client import AgentAPIClient
from core.inventory import (
    get_installed_software,
    get_installed_software_threats,
    get_runtime_security_threats,
    get_network_security_threats,
    get_security_status,
)


CONFIG_FILE = Path(__file__).parent / "config.json"
OFFLINE_METRICS_FILE = Path(__file__).parent / "offline_metrics.json"


def get_cpu_model():
    """Retrieve the CPU model name."""
    try:
        if platform.system() == "Windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
            return cpu_name.strip()
    except Exception:
        pass

    return platform.processor() or "Unknown CPU"


def get_local_ip():
    """Determine the primary local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def collect_system_info():
    """Gather basic hardware and OS info for registration."""
    hostname = socket.gethostname()
    ip_address = get_local_ip()
    operating_system = f"{platform.system()} {platform.release()} (v{platform.version()})"
    cpu_model = get_cpu_model()
    cpu_cores = psutil.cpu_count(logical=False) or os.cpu_count() or 1
    ram_total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)

    try:
        disk_root = "C:\\" if platform.system() == "Windows" else "/"
        disk_total_gb = round(psutil.disk_usage(disk_root).total / (1024 ** 3), 2)
    except Exception:
        disk_total_gb = 0.0

    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "operating_system": operating_system,
        "cpu_model": cpu_model,
        "cpu_cores": cpu_cores,
        "ram_total_gb": ram_total_gb,
        "disk_total_gb": disk_total_gb,
    }


def collect_hardware_details():
    """Gather detailed RAM and disk specifications using WMI on Windows."""
    ram_details = "N/A"
    disk_details = "N/A"

    if platform.system() == "Windows":
        try:
            import wmi
            w = wmi.WMI()

            # RAM Details
            ram_info = []
            for mem in w.Win32_PhysicalMemory():
                cap = round(int(mem.Capacity) / (1024 ** 3), 1)
                speed = getattr(mem, 'Speed', 'N/A')
                mfg = getattr(mem, 'Manufacturer', 'N/A') or 'N/A'
                mfg_clean = mfg.strip() if isinstance(mfg, str) else str(mfg)
                ram_info.append(f"{cap}GB {speed}MHz ({mfg_clean})")
            if ram_info:
                ram_details = ", ".join(ram_info)

            # Disk Details
            disk_info = []
            for disk in w.Win32_DiskDrive():
                model = getattr(disk, 'Model', 'Generic Disk') or 'Generic Disk'
                model_clean = model.strip() if isinstance(model, str) else str(model)
                size = round(int(getattr(disk, 'Size', 0)) / (1024 ** 3), 1)
                disk_info.append(f"{model_clean} ({size}GB)")
            if disk_info:
                disk_details = ", ".join(disk_info)
        except Exception as e:
            ram_details = f"Erro ao coletar: {e}"
            disk_details = f"Erro ao coletar: {e}"

    return ram_details, disk_details


def save_offline_metric(cpu, ram, disk, antivirus_active=True, firewall_active=True, threat_indicators=None):
    """Persist a metric snapshot locally when the backend is offline."""
    import datetime

    metric_entry = {
        "cpu_percent": cpu,
        "ram_percent": ram,
        "disk_percent": disk,
        "antivirus_active": antivirus_active,
        "firewall_active": firewall_active,
        "threat_indicators": threat_indicators or [],
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    data = []
    if OFFLINE_METRICS_FILE.exists():
        try:
            with open(OFFLINE_METRICS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except Exception:
            data = []

    data.append(metric_entry)
    if len(data) > 1000:
        data = data[-1000:]

    try:
        with open(OFFLINE_METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[-] Error saving local metrics buffer: {e}")


def get_offline_metrics():
    """Read the local JSON buffer."""
    if not OFFLINE_METRICS_FILE.exists():
        return []

    try:
        with open(OFFLINE_METRICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def clear_offline_metrics():
    """Delete the local JSON buffer."""
    if OFFLINE_METRICS_FILE.exists():
        try:
            OFFLINE_METRICS_FILE.unlink()
        except Exception as e:
            print(f"[-] Error clearing local buffer: {e}")


def run_telemetry_loop(config):
    """
    Continuous loop that reports heartbeats, metrics and software inventory.
    """
    print("\n" + "=" * 60)
    print("                 InfraMind Agent - Telemetry Daemon          ")
    print("=" * 60)
    print("Starting periodic monitoring loop...")
    print("  -> Heartbeat: every 60 seconds")
    print("  -> Metrics: every 15 seconds")
    print("Press Ctrl+C to stop the agent.")
    print("-" * 60)

    api_client = AgentAPIClient(config["backend_url"])
    api_key = config["api_key"]

    last_heartbeat = 0
    last_metrics = 0
    last_inventory = 0
    is_online = True
    reconnect_check_interval = 30

    ram_details, disk_details = collect_hardware_details()

    try:
        while True:
            now = time.time()

            heartbeat_due = now - last_heartbeat >= (60 if is_online else reconnect_check_interval)
            if heartbeat_due:
                success, response = api_client.send_heartbeat(api_key, ram_details=ram_details, disk_details=disk_details)
                if success:
                    if not is_online:
                        print(f"[+] [{time.strftime('%H:%M:%S')}] Connectivity restored!")
                        is_online = True

                        cached = get_offline_metrics()
                        if cached:
                            print(f"[*] [{time.strftime('%H:%M:%S')}] Sending {len(cached)} offline metrics...")
                            bulk_success, bulk_resp = api_client.send_bulk_metrics(api_key, cached)
                            if bulk_success:
                                print(f"[+] [{time.strftime('%H:%M:%S')}] Offline batch sent successfully.")
                                clear_offline_metrics()
                            else:
                                print(f"[-] [{time.strftime('%H:%M:%S')}] Failed to send offline batch: {bulk_resp}")

                    print(f"[+] [{time.strftime('%H:%M:%S')}] Heartbeat sent successfully.")
                else:
                    # Detect if backend rejected the API key (unauthorized/invalid key)
                    if response and any(kw in response for kw in ["Chave de API", "API key", "inválida", "not registered", "Não autorizado"]):
                        print("\n[!] A chave de API desta máquina foi rejeitada pelo servidor.")
                        print("[*] Removendo configuração inválida para forçar um novo registro...")
                        if CONFIG_FILE.exists():
                            try:
                                CONFIG_FILE.unlink()
                            except Exception:
                                pass
                        print("[*] Reiniciando agente em 3 segundos...")
                        time.sleep(3)
                        os.execv(sys.executable, [sys.executable] + sys.argv)

                    if is_online:
                        print(f"[-] [{time.strftime('%H:%M:%S')}] Connection lost. Switching to offline mode.")
                        is_online = False
                    print(f"[-] [{time.strftime('%H:%M:%S')}] Backend unavailable: {response}")

                last_heartbeat = now

            if now - last_metrics >= 15:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                try:
                    disk_root = "C:\\" if platform.system() == "Windows" else "/"
                    disk = psutil.disk_usage(disk_root).percent
                except Exception:
                    disk = 0

                sec = get_security_status()
                av = sec["antivirus_active"]
                fw = sec["firewall_active"]
                threat_indicators = get_runtime_security_threats() + get_network_security_threats()

                if is_online:
                    success, response = api_client.send_metrics(
                        api_key, cpu, ram, disk, av, fw, threat_indicators, ram_details=ram_details, disk_details=disk_details
                    )
                    if success:
                        print(
                            f"[+] [{time.strftime('%H:%M:%S')}] Metrics sent -> "
                            f"CPU: {cpu}%, RAM: {ram}%, Disk: {disk}%, AV: {av}, FW: {fw}, Threats: {len(threat_indicators)}"
                        )
                    else:
                        if response and any(kw in response for kw in ["Chave de API", "API key", "inválida", "not registered", "Não autorizado"]):
                            print("\n[!] A chave de API desta máquina foi rejeitada pelo servidor ao enviar métricas.")
                            print("[*] Removendo configuração inválida para forçar um novo registro...")
                            if CONFIG_FILE.exists():
                                try:
                                    CONFIG_FILE.unlink()
                                except Exception:
                                    pass
                            print("[*] Reiniciando agente em 3 segundos...")
                            time.sleep(3)
                            os.execv(sys.executable, [sys.executable] + sys.argv)

                        print(f"[-] [{time.strftime('%H:%M:%S')}] Failed to send metrics. Saving to buffer.")
                        save_offline_metric(cpu, ram, disk, av, fw, threat_indicators)
                        is_online = False
                else:
                    print(
                        f"[*] [{time.strftime('%H:%M:%S')}] Offline mode: metrics cached locally -> "
                        f"CPU: {cpu}%, RAM: {ram}%, Disk: {disk}%, AV: {av}, FW: {fw}, Threats: {len(threat_indicators)}"
                    )
                    save_offline_metric(cpu, ram, disk, av, fw, threat_indicators)

                last_metrics = now

            if is_online and (now - last_inventory >= 86400 or last_inventory == 0):
                print(f"[*] [{time.strftime('%H:%M:%S')}] Scanning installed software inventory...")
                softwares = get_installed_software()
                inventory_threats = get_installed_software_threats(softwares)
                print(f"[+] [{time.strftime('%H:%M:%S')}] Found {len(softwares)} softwares. Sending to backend...")
                inv_success, inv_resp = api_client.send_inventory(api_key, softwares, inventory_threats)
                if inv_success:
                    print(
                        f"[+] [{time.strftime('%H:%M:%S')}] Software inventory sent successfully. "
                        f"Threats: {len(inventory_threats)}"
                    )
                    last_inventory = now
                else:
                    if inv_resp and any(kw in inv_resp for kw in ["Chave de API", "API key", "inválida", "not registered", "Não autorizado"]):
                        print("\n[!] A chave de API desta máquina foi rejeitada pelo servidor ao enviar inventário.")
                        print("[*] Removendo configuração inválida para forçar um novo registro...")
                        if CONFIG_FILE.exists():
                            try:
                                CONFIG_FILE.unlink()
                            except Exception:
                                pass
                        print("[*] Reiniciando agente em 3 segundos...")
                        time.sleep(3)
                        os.execv(sys.executable, [sys.executable] + sys.argv)

                    print(f"[-] [{time.strftime('%H:%M:%S')}] Failed to send inventory: {inv_resp}")
                    last_inventory = now - 82800

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Monitoring stopped by user. Shutting down agent...")
        sys.exit(0)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="InfraMind Agent - Setup & Registration")
    parser.add_argument('--backend', '-b', type=str, help='Backend server URL')
    parser.add_argument('--token', '-t', type=str, help='Company registration token')
    args = parser.parse_args()

    backend_url = args.backend
    token = args.token

    config = {}
    current_hostname = socket.gethostname()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Se o hostname atual for diferente do configurado no JSON,
            # significa que a pasta do agente foi copiada para uma nova máquina.
            # Limpamos as chaves antigas para forçar um novo registro automático com o nome correto.
            if config.get("hostname") and config.get("hostname").lower() != current_hostname.lower():
                print(f"[!] Aviso: O nome desta máquina ({current_hostname}) é diferente do configurado ({config.get('hostname')}).")
                print("[*] Identificada nova estação de trabalho. Forçando novo auto-registro...")
                config.pop("api_key", None)
                config.pop("hostname", None)
                config.pop("company", None)
            
            # Se já estiver registrado e com a chave correta, inicia o monitoramento
            if config.get("api_key") and config.get("backend_url"):
                print("Agente já registrado!")
                print(f"Empresa: {config.get('company')}")
                print(f"Máquina: {config.get('hostname')}")
                print(f"Chave de API: {config.get('api_key')}")
                print(f"Servidor: {config.get('backend_url')}")
                print("-" * 60)
                run_telemetry_loop(config)
                return
            
            # Se houver configuração parcial, carrega os dados
            if not backend_url and config.get("backend_url"):
                backend_url = config.get("backend_url")
            if not token and config.get("registration_token"):
                token = config.get("registration_token")
        except Exception as e:
            print(f"Erro ao ler arquivo de configuração: {e}")
            print("Prosseguindo com novas verificações de registro...")

    print("=" * 60)
    print("                 InfraMind Agent - Configuração & Registro            ")
    print("=" * 60)

    # Determinar se deve ser feito registro silencioso
    is_silent = bool(backend_url and token)

    if is_silent:
        print("[*] Parâmetros de registro silencioso detectados.")
        print(f"    URL do Servidor: {backend_url}")
        print(f"    Token da Empresa: {token}")
    else:
        print("Nenhum parâmetro silencioso. Iniciando assistente interativo.")
        print("Coletando especificações do computador...")
        specs = collect_system_info()
        print(f"  Nome da Máquina: {specs['hostname']}")
        print(f"  IP Local: {specs['ip_address']}")
        print(f"  Sistema Operacional: {specs['operating_system']}")
        print(f"  Processador: {specs['cpu_model']} ({specs['cpu_cores']} núcleos)")
        print(f"  Memória RAM: {specs['ram_total_gb']} GB")
        print(f"  Disco Principal: {specs['disk_total_gb']} GB")
        print("-" * 60)

        default_backend = backend_url or "http://192.168.0.63:8000"
        input_backend = input(f"Digite a URL do Servidor Backend [{default_backend}]: ").strip()
        if input_backend:
            backend_url = input_backend
        else:
            backend_url = default_backend

        input_token = input("Digite o Token de Registro da Empresa: ").strip()
        if input_token:
            token = input_token
        
        if not token:
            print("Erro: O Token de Registro da Empresa é obrigatório para cadastrar a máquina.")
            sys.exit(1)

    print("\nCadastrando a máquina no servidor...")
    specs = collect_system_info()
    ram_details, disk_details = collect_hardware_details()
    client = AgentAPIClient(backend_url)
    result, error = client.register(
        hostname=specs["hostname"],
        ip_address=specs["ip_address"],
        operating_system=specs["operating_system"],
        cpu_model=specs["cpu_model"],
        cpu_cores=specs["cpu_cores"],
        ram_total=specs["ram_total_gb"],
        disk_total=specs["disk_total_gb"],
        registration_token=token,
        ram_details=ram_details,
        disk_details=disk_details,
    )

    if error:
        print(f"\n[-] Erro de registro: {error}")
        sys.exit(1)

    config_data = {
        "backend_url": backend_url,
        "api_key": result["api_key"],
        "hostname": result["hostname"],
        "company": result["company"],
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        print("\n[+] Sucesso! Agente registrado com sucesso.")
        print(f"    Empresa: {result['company']}")
        print(f"    Máquina cadastrada como: {result['hostname']}")
        print("    Chave de API salva em config.json.")
        print("=" * 60)

        run_telemetry_loop(config_data)
    except Exception as e:
        print(f"\n[-] Erro ao salvar arquivo de configuração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
