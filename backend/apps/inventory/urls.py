from django.urls import path
from apps.inventory.views import AgentInventoryView

urlpatterns = [
    path('api/agent/inventory', AgentInventoryView.as_view(), name='agent_inventory'),
]
