import socket
import threading
import time

print("=" * 60)
print("     InfraMind - Simulador de Conexão de Rede Suspeita")
print("=" * 60)
print("Este script manterá uma conexão TCP ativa na porta 4444 por 30 segundos.")
print("Isso dará tempo suficiente para o agente do InfraMind varrer a porta")
print("e enviar o alerta de segurança ao backend.")
print("-" * 60)

def start_listener():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 4444))
        server.listen(1)
        conn, addr = server.accept()
        time.sleep(35)
        conn.close()
        server.close()
    except Exception as e:
        pass

# Inicia o escutador em segundo plano
t = threading.Thread(target=start_listener, daemon=True)
t.start()
time.sleep(1) # Aguarda o escutador iniciar

# Inicia o cliente para estabelecer a conexão (ESTABLISHED)
try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 4444))
    print("[+] Conexão TCP estabelecida com sucesso na porta 4444!")
    print("[*] Aguardando 30 segundos com a conexão ativa...")
    
    # Mantém a conexão ativa por 30 segundos
    for i in range(30, 0, -1):
        print(f"\rTempo restante: {i}s...", end="")
        time.sleep(1)
    
    print("\n[-] Fechando conexão.")
    client.close()
except Exception as e:
    print(f"\n[-] Erro ao conectar: {e}")
    print("Certifique-se de que nenhuma outra aplicação esteja usando a porta 4444.")

print("=" * 60)
