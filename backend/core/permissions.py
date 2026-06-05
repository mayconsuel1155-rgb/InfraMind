from rest_framework import permissions
from apps.agents.models import Machine
from django.contrib.auth import get_user_model

User = get_user_model()

class IsAgent(permissions.BasePermission):
    """
    Allows access only to registered machine agents (via API Key).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            isinstance(request.user, Machine)
        )

class IsPortalUser(permissions.BasePermission):
    """
    Allows access only to authenticated portal users (via JWT/Session).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            isinstance(request.user, User)
        )
