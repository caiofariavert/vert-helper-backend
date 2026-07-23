from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Permite acesso apenas a superusuários."""

    message = "Acesso restrito a superusuários."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
