from django.urls import path

from apps.companies.views import management_console_view
from apps.companies.views_agent import download_agent_installer


urlpatterns = [
    path('management/', management_console_view, name='management_console'),
    path('management/download-agent/<int:company_id>/', download_agent_installer, name='download_agent_installer'),
]
