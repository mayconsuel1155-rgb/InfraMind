import socket
import sys
from django.db import connections
from django.db.utils import OperationalError
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class DummyColor:
        def __getattr__(self, name): return ""
    Fore = Style = DummyColor()

def check_port(port=8000):
    print(f"[*] Verificando porta {port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('127.0.0.1', port))
        if result == 0:
            print(f"{Fore.RED}[X] ERRO: A porta {port} já está em uso.{Style.RESET_ALL}")
            print(f"    Solução: Feche o programa que está usando a porta {port} ou configure o InfraMind para usar outra.")
            return False
        else:
            print(f"{Fore.GREEN}[+] OK: A porta {port} está livre.{Style.RESET_ALL}")
            return True

def check_database():
    print("[*] Verificando conexão com o Banco de Dados...")
    db_conn = connections['default']
    try:
        c = db_conn.cursor()
        print(f"{Fore.GREEN}[+] OK: Banco de dados conectado com sucesso ({db_conn.vendor}).{Style.RESET_ALL}")
        return True
    except OperationalError as e:
        print(f"{Fore.RED}[X] ERRO: Não foi possível conectar ao banco de dados.{Style.RESET_ALL}")
        print(f"    Detalhes: {e}")
        print(f"    Solução: Verifique se o PostgreSQL está rodando ou se o arquivo SQLite tem permissão de escrita.")
        return False

def check_migrations():
    print("[*] Verificando migrações pendentes...")
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        call_command('showmigrations', format='plan', stdout=out)
        if '[ ]' in out.getvalue():
            print(f"{Fore.YELLOW}[!] AVISO: Existem migrações pendentes.{Style.RESET_ALL}")
            print(f"    Solução: O instalador ou o comando 'migrate' deve ser executado.")
            return False
        else:
            print(f"{Fore.GREEN}[+] OK: Banco de dados está atualizado.{Style.RESET_ALL}")
            return True
    except Exception as e:
        print(f"{Fore.RED}[X] ERRO ao checar migrações: {e}{Style.RESET_ALL}")
        return False

def run_all_diagnostics():
    print("============================================================")
    print("              INFRAMIND - SYSTEM DIAGNOSTIC                 ")
    print("============================================================")
    
    port_ok = check_port(8000)
    db_ok = check_database()
    mig_ok = False
    if db_ok:
        mig_ok = check_migrations()

    print("\n[ Resumo do Diagnóstico ]")
    if port_ok and db_ok and mig_ok:
        print(f"{Fore.GREEN}[+] Sistema pronto para execução.{Style.RESET_ALL}")
        sys.exit(0)
    else:
        print(f"{Fore.RED}[-] Problemas encontrados. Veja as soluções acima.{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == '__main__':
    run_all_diagnostics()
