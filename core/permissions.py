"""
DRF permission classes for the CRM project.

Usage in ViewSets:
    permission_classes = [IsAuthenticated, IsSalesExecutive]
"""

from rest_framework.permissions import BasePermission


class IsSalesRep(BasePermission):
    """Allow access to users with any sales role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_sales_rep()
            or request.user.is_sales_manager()
            or request.user.is_sales_executive()
        )


class IsSalesManager(BasePermission):
    """Allow access to sales managers and above."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_sales_manager() or request.user.is_sales_executive()


class IsSalesExecutive(BasePermission):
    """Allow access to sales executives only."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_sales_executive()


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission: allow full access to the object's owner,
    read-only for everyone else.

    Expects the object to have a `created_by` or `assigned_to` attribute.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        if hasattr(obj, "can_be_edited_by"):
            return obj.can_be_edited_by(request.user)

        return (
            getattr(obj, "created_by", None) == request.user
            or getattr(obj, "assigned_to", None) == request.user
        )
