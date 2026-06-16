from django.urls import path
from . import views

urlpatterns = [
    path('', views.compliance_dashboard, name='compliance_dashboard'),
    path('report/executive/', views.report_executive, name='compliance_report_executive'),
    path('report/audit/', views.report_audit, name='compliance_report_audit'),
]
