"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from apps.accounts.views import login_view, logout_view
from apps.monitoring.views import (
    dashboard_view,
    machine_list_view,
    machine_detail_view,
    machine_delete_view,
    alerts_list_view,
    resolve_alert_view,
)
from apps.tickets.views import tickets_list_view, ticket_detail_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # JWT Auth Endpoints
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Agent Endpoints
    path('api/', include('apps.agents.urls')),
    
    # Web Portal (HTML Interface)
    path('', dashboard_view, name='dashboard'),
    path('machines/', machine_list_view, name='machine_list'),
    path('machines/<int:pk>/', machine_detail_view, name='machine_detail'),
    path('machines/<int:pk>/delete/', machine_delete_view, name='machine_delete'),
    path('alerts/', alerts_list_view, name='alerts_list'),
    path('alerts/<int:pk>/resolve/', resolve_alert_view, name='resolve_alert'),
    
    # Tickets
    path('tickets/', tickets_list_view, name='tickets_list'),
    path('tickets/<int:pk>/', ticket_detail_view, name='ticket_detail'),
    
    # Portal Auth & Privacy (LGPD)
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('accounts/', include('apps.accounts.urls')),
    
    # Integrations (AI Configuration)
    path('', include('apps.integrations.urls')),
    
    # SaaS Management Console
    path('', include('apps.companies.urls')),
    
    # Inventory
    path('', include('apps.inventory.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
