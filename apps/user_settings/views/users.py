from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth import get_user_model

from core.models import Role, UserRole
from .base import SettingsBaseMixin
from .general import AdminRequiredMixin
from ..forms import UserCreateForm, UserEditForm

User = get_user_model()


class UserListView(SettingsBaseMixin, AdminRequiredMixin, ListView):
    """User management list page."""

    model = User
    template_name = 'settings/users/list.html'
    context_object_name = 'users'
    paginate_by = 20
    settings_section = 'general'

    def get_queryset(self):
        qs = User.objects.prefetch_related(
            Prefetch('user_roles', queryset=UserRole.objects.select_related('role'))
        ).select_related('sales_team').order_by('-date_joined')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )

        role = self.request.GET.get('role', '').strip()
        if role:
            qs = qs.filter(user_roles__role__name=role).distinct()

        status = self.request.GET.get('status', '').strip()
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_role'] = self.request.GET.get('role', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class UserCreateView(SettingsBaseMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new user account."""

    model = User
    form_class = UserCreateForm
    template_name = 'settings/users/form.html'
    success_message = "User '%(username)s' was created successfully."
    success_url = reverse_lazy('settings:users:list')
    settings_section = 'general'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit_mode'] = False
        context['page_title'] = 'Create User'
        return context

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        selected_roles = form.cleaned_data.get('roles', [])
        for role in selected_roles:
            UserRole.objects.create(
                user=self.object,
                role=role,
                assigned_by=self.request.user,
            )
        return response


class UserEditView(SettingsBaseMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edit an existing user's details and roles."""

    model = User
    form_class = UserEditForm
    template_name = 'settings/users/form.html'
    success_url = reverse_lazy('settings:users:list')
    settings_section = 'general'

    def get_success_message(self, cleaned_data):
        return f"User '{self.object.username}' was updated successfully."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit_mode'] = True
        context['page_title'] = f"Edit {self.object.get_full_name() or self.object.username}"
        return context

    @transaction.atomic
    def form_valid(self, form):
        # Guard: prevent removing own Owner role
        if self.object.pk == self.request.user.pk:
            selected_role_names = {r.name for r in form.cleaned_data.get('roles', [])}
            if not form.cleaned_data.get('is_active', True):
                messages.error(self.request, 'You cannot deactivate your own account.')
                return self.form_invalid(form)

        response = super().form_valid(form)

        selected_roles = set(form.cleaned_data.get('roles', []))
        current_roles = set(
            ur.role for ur in self.object.user_roles.select_related('role')
        )

        # Remove roles that were unchecked
        for role in current_roles - selected_roles:
            self.object.user_roles.filter(role=role).delete()

        # Add newly selected roles
        for role in selected_roles - current_roles:
            UserRole.objects.create(
                user=self.object,
                role=role,
                assigned_by=self.request.user,
            )

        return response


class UserToggleActiveView(AdminRequiredMixin, View):
    """POST-only: toggle a user's is_active flag."""

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        if target.pk == request.user.pk:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('settings:users:list')

        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])

        verb = 'activated' if target.is_active else 'deactivated'
        name = target.get_full_name() or target.username
        messages.success(request, f"User '{name}' has been {verb}.")
        return redirect('settings:users:list')


# URL patterns for users section
users_urls = [
    path('', UserListView.as_view(), name='list'),
    path('create/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/edit/', UserEditView.as_view(), name='user_edit'),
    path('<int:pk>/toggle-active/', UserToggleActiveView.as_view(), name='user_toggle_active'),
]
