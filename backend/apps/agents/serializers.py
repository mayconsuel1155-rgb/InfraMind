from rest_framework import serializers

class AgentRegisterSerializer(serializers.Serializer):
    hostname = serializers.CharField(max_length=200)
    ip_address = serializers.IPAddressField()
    operating_system = serializers.CharField(max_length=200)
    cpu_model = serializers.CharField(max_length=200)
    cpu_cores = serializers.IntegerField(min_value=1)
    ram_total_gb = serializers.FloatField(min_value=0.1)
    disk_total_gb = serializers.FloatField(min_value=0.1)
    registration_token = serializers.CharField(max_length=64)
    ram_details = serializers.CharField(required=False, default='', allow_blank=True)
    disk_details = serializers.CharField(required=False, default='', allow_blank=True)

class AgentMetricsSerializer(serializers.Serializer):
    cpu_percent = serializers.FloatField(min_value=0.0, max_value=100.0)
    ram_percent = serializers.FloatField(min_value=0.0, max_value=100.0)
    disk_percent = serializers.FloatField(min_value=0.0, max_value=100.0)
    collected_at = serializers.DateTimeField(required=False)
    antivirus_active = serializers.BooleanField(required=False, default=True)
    firewall_active = serializers.BooleanField(required=False, default=True)
    threat_indicators = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )

