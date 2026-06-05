import os
import sys
import time
import json
import math
import tempfile
import threading
import multiprocessing
from pathlib import Path

# Add parent path to allow imports from services if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import psutil
    import requests
except ImportError:
    print("[-] Erro: Dependências (psutil, requests) não encontradas.")
    print("    Por favor, ative o ambiente virtual e instale as dependências:")
    print("    venv\\Scripts\\activate.bat")
    print("    pip install -r requirements.txt")
    sys.exit(1)

from services.api_client import AgentAPIClient

CONFIG_FILE = Path(__file__).parent / "config.json"


# CPU Worker
def cpu_stress_worker(stop_event):
    while not stop_event.is_set():
        # Loops de cálculo matemático intensivo para elevar a CPU
        _ = math.sqrt(math.sin(12345.67) * math.cos(76543.21))


# RAM Worker
def ram_stress_worker(target_percent, stop_event):
    allocated = []
    chunk_size = 50 * 1024 * 1024  # Alocações em blocos de 50MB
    try:
        while not stop_event.is_set():
            mem = psutil.virtual_memory()
            if mem.percent < target_percent:
                allocated.append(bytearray(chunk_size))
                time.sleep(0.05)
            elif mem.percent > target_percent + 1.5:
                if allocated:
                    allocated.pop()
                time.sleep(0.2)
            else:
                time.sleep(0.2)
    except MemoryError:
        print("\n[-] Memória física máxima atingida para o processo.")
    finally:
        allocated.clear()


# Disk Worker
def disk_stress_worker(target_percent, stop_event):
    temp_dir = tempfile.get_tempdir()
    filepath = os.path.join(temp_dir, "inframind_stress_temp.dat")
    chunk_size = 50 * 1024 * 1024  # Escritas de 50MB por vez
    
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

    try:
        f = open(filepath, "wb")
        while not stop_event.is_set():
            disk = psutil.disk_usage(temp_dir)
            if disk.percent < target_percent:
                f.write(os.urandom(chunk_size))
                f.flush()
            else:
                time.sleep(0.2)
        f.close()
    except Exception as e:
        print(f"\n[-] Erro ao escrever no disco: {e}")
    finally:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass


# Live Monitor
def monitor_reporter(stop_event):
    while not stop_event.is_set():
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(tempfile.get_tempdir()).percent
        print(f"\r[STATUS LOCAL] CPU: {cpu:.1f}% | RAM: {mem:.1f}% | DISCO: {disk:.1f}%     ", end="", flush=True)


def send_simulated_metrics(config, duration):
    client = AgentAPIClient(config["backend_url"])
    api_key = config["api_key"]
    print(f"\n[*] Iniciando envio de métricas virtuais de estresse...")
    print(f"    Backend: {config['backend_url']}")
    print(f"    Chave da Máquina: {api_key}")
    print(f"    Duração: {duration} segundos (Envio a cada 5s)")
    print("-" * 60)
    
    start_time = time.time()
    cpu = 98.0
    ram = 95.0
    disk = 85.0
    
    try:
        while time.time() - start_time < duration:
            success, resp = client.send_metrics(
                api_key=api_key,
                cpu_percent=cpu,
                ram_percent=ram,
                disk_percent=disk,
                antivirus_active=True,
                firewall_active=True
            )
            if success:
                print(f"[+] Métricas simuladas enviadas -> CPU: {cpu}%, RAM: {ram}%, Disco: {disk}%")
            else:
                print(f"[-] Erro ao enviar métricas de simulação: {resp}")
            time.sleep(5)
            
        print("\n[*] Duração da simulação concluída. Enviando métricas normais de recuperação...")
        success, resp = client.send_metrics(
            api_key=api_key,
            cpu_percent=12.0,
            ram_percent=45.0,
            disk_percent=30.0,
            antivirus_active=True,
            firewall_active=True
        )
        if success:
            print("[+] Métricas de recuperação enviadas (CPU: 12%, RAM: 45%, Disco: 30%). Alertas serão resolvidos.")
        else:
            print(f"[-] Erro ao enviar métricas de recuperação: {resp}")
            
    except KeyboardInterrupt:
        print("\n[!] Simulação interrompida. Enviando métricas normais de recuperação antes de fechar...")
        client.send_metrics(
            api_key=api_key,
            cpu_percent=12.0,
            ram_percent=45.0,
            disk_percent=30.0,
            antivirus_active=True,
            firewall_active=True
        )
        print("[+] Métricas de recuperação enviadas. Saindo...")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="INFRAMIND - SISTEMA DE ESTRESSE E TESTE")
    parser.add_argument('--mode', choices=['1', '2'], help='Modo de teste: 1 para Estresse Real, 2 para Simulação Virtual')
    parser.add_argument('--duration', type=int, default=60, help='Duração do teste em segundos')
    parser.add_argument('--cpu', action='store_true', help='Executar estresse de CPU (apenas no modo 1)')
    parser.add_argument('--ram', action='store_true', help='Executar estresse de RAM (apenas no modo 1)')
    parser.add_argument('--disk', action='store_true', help='Executar estresse de Disco (apenas no modo 1)')
    parser.add_argument('--all', action='store_true', help='Estressar CPU, RAM e Disco (apenas no modo 1)')
    args = parser.parse_args()

    print("=" * 60)
    print("                 INFRAMIND - SISTEMA DE ESTRESSE E TESTE            ")
    print("=" * 60)
    
    # Load config.json
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[-] Erro ao ler config.json: {e}")
            
    if args.mode:
        opcao = args.mode
    else:
        print("[1] Estresse Físico Real (Forçar CPU, RAM e Disco da Máquina)")
        print("[2] Simulação Virtual de Métricas Altas (Apenas chamadas de API do Agente)")
        print("[3] Sair")
        print("-" * 60)
        try:
            opcao = input("Selecione a opção desejada (1-3): ").strip()
        except KeyboardInterrupt:
            print("\nSaindo...")
            return

    if opcao == "2":
        if not config.get("api_key") or not config.get("backend_url"):
            print("[-] Erro: É necessário ter o config.json do agente configurado para simulação de API.")
            return
        
        duracao = args.duration if args.mode else 60
        if not args.mode:
            try:
                duracao = int(input("Digite a duração do teste em segundos (padrão: 60): ").strip() or "60")
            except ValueError:
                duracao = 60
        send_simulated_metrics(config, duracao)
        
    elif opcao == "1":
        if args.mode:
            stress_cpu = args.cpu or args.all
            stress_ram = args.ram or args.all
            stress_disk = args.disk or args.all
            # If nothing specified, default to all
            if not (args.cpu or args.ram or args.disk or args.all):
                stress_cpu = stress_ram = stress_disk = True
            duracao = args.duration
        else:
            print("\n--- Configurações de Estresse Físico ---")
            try:
                stress_cpu = input("Estressar CPU? (S/N) [padrão: S]: ").strip().upper() != "N"
                stress_ram = input("Estressar RAM? (S/N) [padrão: S]: ").strip().upper() != "N"
                stress_disk = input("Estressar Disco? (S/N) [padrão: S]: ").strip().upper() != "N"
                duracao = int(input("Digite a duração em segundos (padrão: 60): ").strip() or "60")
            except (ValueError, KeyboardInterrupt):
                print("\nOperação cancelada.")
                return

        stop_event = multiprocessing.Event()
        threads = []
        processes = []

        # Monitor de console
        mon_thread = threading.Thread(target=monitor_reporter, args=(stop_event,))
        mon_thread.daemon = True
        mon_thread.start()

        print(f"\n[*] Iniciando estresse físico por {duracao} segundos...")
        if stress_cpu:
            cores = multiprocessing.cpu_count()
            print(f"[*] Iniciando estresse de CPU em {cores} núcleos lógicos...")
            for _ in range(cores):
                p = multiprocessing.Process(target=cpu_stress_worker, args=(stop_event,))
                p.daemon = True
                p.start()
                processes.append(p)

        if stress_ram:
            print("[*] Iniciando estresse de RAM (Alvo: 92% de uso)...")
            t = threading.Thread(target=ram_stress_worker, args=(92.0, stop_event))
            t.daemon = True
            t.start()
            threads.append(t)

        if stress_disk:
            print("[*] Iniciando estresse de Disco (Alvo: 85% de uso)...")
            t = threading.Thread(target=disk_stress_worker, args=(85.0, stop_event))
            t.daemon = True
            t.start()
            threads.append(t)

        try:
            # Aguarda a duração do teste
            time.sleep(duracao)
            print("\n[*] Tempo limite atingido. Parando estresse e limpando recursos...")
        except KeyboardInterrupt:
            print("\n[!] Estresse interrompido manualmente pelo usuário. Limpando recursos...")
        finally:
            stop_event.set()
            
            # Aguarda os processos de CPU finalizarem
            for p in processes:
                p.join(timeout=2)
                if p.is_alive():
                    p.terminate()
            
            # Aguarda threads limparem arquivos/memória
            for t in threads:
                t.join(timeout=2)
                
            print("\n[+] Recursos limpos. A máquina voltou ao estado normal.")
            
    else:
        print("Saindo...")


if __name__ == "__main__":
    # Importante no Windows para evitar recursão infinita ao criar processos
    multiprocessing.freeze_support()
    main()
