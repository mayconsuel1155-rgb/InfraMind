from django.urls import path
from apps.agents.views import AgentRegisterView, AgentHeartbeatView, AgentMetricsView

urlpatterns = [
    path('agent/register', AgentRegisterView.as_view(), name='agent_register'),
    path('agent/heartbeat', AgentHeartbeatView.as_view(), name='agent_heartbeat'),
    path('agent/metrics', AgentMetricsView.as_view(), name='agent_metrics'),
]
