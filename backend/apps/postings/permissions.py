from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Defense in depth alongside the owner-scoped queryset in the
    viewset — belt and suspenders, not the only thing standing between a
    submitter and someone else's posting.
    """

    def has_object_permission(self, request, view, obj):
        return obj.submitter_id == request.user.id
