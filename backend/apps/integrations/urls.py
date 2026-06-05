from django.urls import path
from apps.integrations.views import ai_config_view, api_test_ai, alert_ai_diagnosis_view

urlpatterns = [
    path('settings/ai/', ai_config_view, name='ai_config'),
    path('api/integrations/ai/test/', api_test_ai, name='api_test_ai'),
    path('api/alerts/<int:pk>/ai-diagnosis/', alert_ai_diagnosis_view, name='alert_ai_diagnosis'),
]
