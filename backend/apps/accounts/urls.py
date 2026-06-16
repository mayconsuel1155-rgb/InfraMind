from django.urls import path
from apps.accounts.views import (
    lgpd_consent_view,
    lgpd_export_data_view,
    lgpd_anonymize_user_view,
    user_reset_password_view,
    mfa_setup,
    mfa_verify,
)

urlpatterns = [
    path('lgpd-consent/', lgpd_consent_view, name='lgpd_consent'),
    path('export-data/', lgpd_export_data_view, name='lgpd_export_own_data'),
    path('export-data/<int:user_id>/', lgpd_export_data_view, name='lgpd_export_user_data'),
    path('anonymize/<int:user_id>/', lgpd_anonymize_user_view, name='lgpd_anonymize_user'),
    path('reset-password/<int:user_id>/', user_reset_password_view, name='user_reset_password'),
    path('mfa/setup/', mfa_setup, name='mfa_setup'),
    path('mfa/verify/', mfa_verify, name='mfa_verify'),
]
