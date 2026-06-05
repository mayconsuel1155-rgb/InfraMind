from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone

from apps.companies.models import Company
from apps.agents.models import Machine
from apps.agents.serializers import AgentRegisterSerializer, AgentMetricsSerializer
from apps.monitoring.models import Metric
from apps.alerts.models import Alert
from apps.alerts.services import RulesEngineService
from core.authentication import ApiKeyAuthentication
from core.permissions import IsAgent
from core.throttling import AgentRegisterThrottle, AgentHeartbeatThrottle, AgentMetricsThrottle
from apps.inventory.security import sync_security_threat_alerts

class AgentRegisterView(APIView):
    """
    Endpoint for agent self-registration.
    Requires a valid company registration_token.
    Returns the unique api_key for the registered machine.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AgentRegisterThrottle]

    def post(self, request):
        serializer = AgentRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        reg_token = data.pop('registration_token')

        try:
            company = Company.objects.get(registration_token=reg_token, is_active=True)
        except Company.DoesNotExist:
            return Response(
                {"error": "Token de registro inválido ou empresa inativa."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update or create the machine for this company by hostname
        machine, created = Machine.objects.update_or_create(
            company=company,
            hostname=data['hostname'],
            defaults={
                'ip_address': data['ip_address'],
                'operating_system': data['operating_system'],
                'cpu_model': data['cpu_model'],
                'cpu_cores': data['cpu_cores'],
                'ram_total_gb': data['ram_total_gb'],
                'disk_total_gb': data['disk_total_gb'],
                'ram_details': data.get('ram_details', ''),
                'disk_details': data.get('disk_details', ''),
                'status': 'online',
                'last_seen': timezone.now(),
            }
        )

        return Response({
            "message": "Agente registrado com sucesso." if created else "Agente atualizado com sucesso.",
            "api_key": str(machine.api_key),
            "hostname": machine.hostname,
            "company": company.name,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AgentHeartbeatView(APIView):
    """
    Endpoint for periodic agent heartbeat ping.
    Updates the machine's last_seen status and clears offlines.
    """
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAgent]
    throttle_classes = [AgentHeartbeatThrottle]

    def post(self, request):
        machine = request.user
        machine.last_seen = timezone.now()
        
        # If machine was marked offline, restore it to online
        if machine.status == 'offline':
            machine.status = 'online'
            
        update_fields = ['last_seen', 'status']
        ram_details = request.data.get('ram_details') if isinstance(request.data, dict) else None
        disk_details = request.data.get('disk_details') if isinstance(request.data, dict) else None
        
        if ram_details:
            machine.ram_details = ram_details
            update_fields.append('ram_details')
        if disk_details:
            machine.disk_details = disk_details
            update_fields.append('disk_details')
            
        machine.save(update_fields=update_fields)
        
        # Resolve any outstanding machine_offline alerts
        Alert.objects.filter(
            machine=machine,
            type='machine_offline',
            is_resolved=False
        ).update(is_resolved=True, resolved_at=timezone.now())

        return Response({"status": "ok", "message": "Heartbeat recebido."})


class AgentMetricsView(APIView):
    """
    Endpoint for agents to report CPU, RAM, and Disk metrics.
    Triggers the Alerts Rules Engine to identify status changes.
    """
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAgent]
    throttle_classes = [AgentMetricsThrottle]

    def post(self, request):
        is_bulk = isinstance(request.data, list)
        
        if is_bulk:
            serializer = AgentMetricsSerializer(data=request.data, many=True)
        else:
            serializer = AgentMetricsSerializer(data=request.data)
            
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        machine = request.user
        
        if is_bulk:
            metrics_created = []
            for item in serializer.validated_data:
                collected_at = item.get('collected_at') or timezone.now()
                metric = Metric.objects.create(
                    machine=machine,
                    cpu_percent=item['cpu_percent'],
                    ram_percent=item['ram_percent'],
                    disk_percent=item['disk_percent'],
                    collected_at=collected_at
                )
                metrics_created.append(metric)
            
            if metrics_created:
                metrics_created.sort(key=lambda x: x.collected_at)
                latest_metric = metrics_created[-1]
            else:
                latest_metric = None
        else:
            data = serializer.validated_data
            collected_at = data.get('collected_at') or timezone.now()
            latest_metric = Metric.objects.create(
                machine=machine,
                cpu_percent=data['cpu_percent'],
                ram_percent=data['ram_percent'],
                disk_percent=data['disk_percent'],
                collected_at=collected_at
            )
        threat_indicators = []
        if is_bulk:
            for item in serializer.validated_data:
                threat_indicators.extend(item.get('threat_indicators', []))
        else:
            threat_indicators = serializer.validated_data.get('threat_indicators', [])

        # Update or create SecurityStatus from latest metric values
        from apps.inventory.models import SecurityStatus
        if is_bulk:
            sorted_data = sorted(serializer.validated_data, key=lambda x: x.get('collected_at') or timezone.now())
            latest_item = sorted_data[-1] if sorted_data else {}
            av_active = latest_item.get('antivirus_active', True)
            fw_active = latest_item.get('firewall_active', True)
        else:
            av_active = serializer.validated_data.get('antivirus_active', True)
            fw_active = serializer.validated_data.get('firewall_active', True)

        SecurityStatus.objects.update_or_create(
            machine=machine,
            defaults={
                'antivirus_active': av_active,
                'firewall_active': fw_active
            }
        )
            
        # Act as heartbeat too
        machine.last_seen = timezone.now()
        if machine.status == 'offline':
            machine.status = 'online'
            
        update_fields = ['last_seen', 'status']
        if isinstance(request.data, dict):
            ram_details = request.data.get('ram_details')
            disk_details = request.data.get('disk_details')
            if ram_details:
                machine.ram_details = ram_details
                update_fields.append('ram_details')
            if disk_details:
                machine.disk_details = disk_details
                update_fields.append('disk_details')
                
        machine.save(update_fields=update_fields)
        
        # Resolve offline alerts
        Alert.objects.filter(
            machine=machine,
            type='machine_offline',
            is_resolved=False
        ).update(is_resolved=True, resolved_at=timezone.now())

        if threat_indicators:
            sync_security_threat_alerts(machine, threat_indicators)
        
        # Run rules evaluation on the latest metric state
        if latest_metric:
            RulesEngineService.evaluate_metrics(latest_metric)
            
        return Response({"status": "ok", "message": "Métricas processadas com sucesso."})
