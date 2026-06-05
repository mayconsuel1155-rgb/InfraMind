from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import InstalledSoftware
from apps.inventory.security import build_software_threats, sync_security_threat_alerts
from core.authentication import ApiKeyAuthentication
from core.permissions import IsAgent


class AgentInventoryView(APIView):
    """
    Endpoint for agents to report installed software and security indicators.
    Accepts either a plain list of software items or a payload with:
    - softwares: list of installed software entries
    - threat_indicators: list of threat payloads detected by the agent
    """

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAgent]

    def post(self, request):
        if isinstance(request.data, dict):
            software_items = request.data.get('softwares', [])
            explicit_threats = request.data.get('threat_indicators', [])
        elif isinstance(request.data, list):
            software_items = request.data
            explicit_threats = []
        else:
            return Response(
                {"error": "Os dados devem ser enviados como uma lista de softwares ou um objeto com a chave 'softwares'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        machine = request.user

        with transaction.atomic():
            InstalledSoftware.objects.filter(machine=machine).delete()

            softwares_to_create = []
            seen_names = set()
            for item in software_items:
                name = item.get('name')
                if not name or not name.strip():
                    continue

                name = name.strip()
                if name in seen_names:
                    continue
                seen_names.add(name)

                softwares_to_create.append(
                    InstalledSoftware(
                        machine=machine,
                        name=name,
                        version=item.get('version', 'N/A') or 'N/A',
                        publisher=item.get('publisher', 'N/A') or 'N/A',
                    )
                )

            if softwares_to_create:
                InstalledSoftware.objects.bulk_create(softwares_to_create)

            detected_threats = build_software_threats(software_items)
            for threat in explicit_threats:
                if isinstance(threat, dict) and threat.get('type') and threat.get('message'):
                    detected_threats.append(threat)

            sync_security_threat_alerts(machine, detected_threats)

        return Response(
            {
                "status": "ok",
                "message": f"Inventario de softwares atualizado com sucesso ({len(softwares_to_create)} itens).",
                "threats_detected": len(detected_threats),
            },
            status=status.HTTP_201_CREATED,
        )
