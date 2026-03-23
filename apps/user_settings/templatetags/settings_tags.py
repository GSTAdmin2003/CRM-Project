from django import template
from django.contrib.auth import get_user_model

User = get_user_model()
register = template.Library()


@register.simple_tag
def user_has_role(user, role_name):
    """Check if a user has a specific role"""
    if not user.is_authenticated:
        return False
    return user.has_role(role_name)


@register.simple_tag
def user_is_admin(user):
    """Check if a user is an admin (staff or Owner)"""
    if not user.is_authenticated:
        return False
    return user.is_staff or user.has_role('Owner') or user.has_role('IT Admin')


@register.filter
def has_role(user, role_name):
    """Template filter to check if user has a role"""
    if not user.is_authenticated:
        return False
    return user.has_role(role_name)