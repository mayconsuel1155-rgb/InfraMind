from django.urls import path

from apps.companies.views import management_console_view


urlpatterns = [
    path('management/', management_console_view, name='management_console'),
]
