from rest_framework import permissions

from apps.accounts.models import User


class IsModeratorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in (User.Role.MODERATOR, User.Role.ADMIN)
        )
