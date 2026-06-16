import os
import sys
import argparse
from pathlib import Path

# Adjust paths if frozen by PyInstaller
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# In standalone mode, we want data to go to ProgramData
PROGRAM_DATA = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
INFRAMIND_DATA_DIR = os.path.join(PROGRAM_DATA, 'InfraMind')
if getattr(sys, 'frozen', False):
    os.makedirs(INFRAMIND_DATA_DIR, exist_ok=True)
    os.environ['INFRAMIND_DATA_DIR'] = INFRAMIND_DATA_DIR

import django
django.setup()

def run_server(port=8000):
    from waitress import serve
    from config.wsgi import application
    print(f"[*] Starting InfraMind Waitress Server on 0.0.0.0:{port}...")
    serve(application, host='0.0.0.0', port=port)

def run_diagnostic():
    from core.diagnostic import run_all_diagnostics
    run_all_diagnostics()

def run_migrations():
    from django.core.management import call_command
    print("[*] Running database migrations...")
    call_command('migrate', interactive=False)

def create_superuser(email, password):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(email=email).exists():
        print(f"[*] Creating superuser {email}...")
        User.objects.create_superuser(email=email, password=password)
        print("[+] Superuser created successfully.")
    else:
        print(f"[*] Superuser {email} already exists.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InfraMind Server CLI")
    parser.add_argument('command', nargs='?', default='runserver', help="Command to run (runserver, diagnose, migrate, createsuperuser)")
    parser.add_argument('--port', type=int, default=8000, help="Port for the server")
    parser.add_argument('--email', type=str, help="Email for createsuperuser")
    parser.add_argument('--password', type=str, help="Password for createsuperuser")
    
    args = parser.parse_args()

    if args.command == 'runserver':
        run_server(args.port)
    elif args.command == 'diagnose':
        run_diagnostic()
    elif args.command == 'migrate':
        run_migrations()
    elif args.command == 'createsuperuser':
        if not args.email or not args.password:
            print("[-] Error: --email and --password are required for createsuperuser")
            sys.exit(1)
        create_superuser(args.email, args.password)
    else:
        print(f"[-] Unknown command: {args.command}")
        sys.exit(1)
