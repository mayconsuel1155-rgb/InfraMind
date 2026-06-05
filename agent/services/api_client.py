import requests
import json
import os
from pathlib import Path

class AgentAPIClient:
    def __init__(self, backend_url):
        self.backend_url = backend_url.rstrip('/')

    def register(self, hostname, ip_address, operating_system, cpu_model, cpu_cores, ram_total, disk_total, registration_token, ram_details=None, disk_details=None):
        url = f"{self.backend_url}/api/agent/register"
        payload = {
            "hostname": hostname,
            "ip_address": ip_address,
            "operating_system": operating_system,
            "cpu_model": cpu_model,
            "cpu_cores": cpu_cores,
            "ram_total_gb": ram_total,
            "disk_total_gb": disk_total,
            "registration_token": registration_token,
            "ram_details": ram_details or "",
            "disk_details": disk_details or ""
        }

        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code in (200, 201):
                return response.json(), None
            else:
                try:
                    error_detail = response.json()
                except ValueError:
                    error_detail = response.text
                return None, f"Erro {response.status_code}: {error_detail}"
        except requests.exceptions.RequestException as e:
            return None, f"Falha de conexão com o servidor: {e}"

    def send_heartbeat(self, api_key, ram_details=None, disk_details=None):
        url = f"{self.backend_url}/api/agent/heartbeat"
        headers = {"Authorization": f"ApiKey {api_key}"}
        payload = {}
        if ram_details:
            payload["ram_details"] = ram_details
        if disk_details:
            payload["disk_details"] = disk_details
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            return response.status_code in (200, 201), response.text
        except Exception as e:
            return False, str(e)

    def send_metrics(self, api_key, cpu_percent, ram_percent, disk_percent, antivirus_active=True, firewall_active=True, threat_indicators=None, ram_details=None, disk_details=None):
        url = f"{self.backend_url}/api/agent/metrics"
        headers = {"Authorization": f"ApiKey {api_key}"}
        payload = {
            "cpu_percent": cpu_percent,
            "ram_percent": ram_percent,
            "disk_percent": disk_percent,
            "antivirus_active": antivirus_active,
            "firewall_active": firewall_active,
            "threat_indicators": threat_indicators or [],
        }
        if ram_details:
            payload["ram_details"] = ram_details
        if disk_details:
            payload["disk_details"] = disk_details
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            return response.status_code in (200, 201), response.text
        except Exception as e:
            return False, str(e)

    def send_bulk_metrics(self, api_key, metrics_list):
        url = f"{self.backend_url}/api/agent/metrics"
        headers = {"Authorization": f"ApiKey {api_key}"}
        try:
            response = requests.post(url, json=metrics_list, headers=headers, timeout=15)
            return response.status_code in (200, 201), response.text
        except Exception as e:
            return False, str(e)

    def send_inventory(self, api_key, software_list, threat_indicators=None):
        url = f"{self.backend_url}/api/agent/inventory"
        headers = {"Authorization": f"ApiKey {api_key}"}
        payload = {
            "softwares": software_list,
            "threat_indicators": threat_indicators or [],
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.status_code in (200, 201), response.text
        except Exception as e:
            return False, str(e)

