from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse_lazy
from core.models import AppRegistry, User


class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)


def custom_logout_view(request):
    """Custom logout view that always shows the logout template"""
    from django.contrib.auth import logout
    from django.shortcuts import render

    if request.user.is_authenticated:
        messages.info(request, 'You have been successfully logged out.')
        logout(request)

    return render(request, 'registration/logged_out.html')


@login_required
def dashboard_view(request):
    """Main dashboard view showing all accessible apps"""
    user_apps = AppRegistry.get_user_apps(request.user)

    context = {
        'user_apps': user_apps,
        'user': request.user,
    }

    return render(request, 'core/dashboard.html', context)


def redirect_to_dashboard(request):
    """Redirect root URL to dashboard"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')


@login_required
def settings_view(request):
    """Settings dashboard view"""
    return render(request, 'core/settings.html', {'user': request.user})


@login_required
def settings_profile_view(request):
    """Unified profile settings view with personal info and password change"""
    from django.contrib.auth.forms import PasswordChangeForm
    from django import forms

    class ProfileForm(forms.ModelForm):
        class Meta:
            model = User
            fields = ['first_name', 'last_name', 'email']
            widgets = {
                'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                'last_name': forms.TextInput(attrs={'class': 'form-control'}),
                'email': forms.EmailInput(attrs={'class': 'form-control'}),
            }

    class CustomPasswordChangeForm(PasswordChangeForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in self.fields:
                self.fields[field].widget.attrs.update({'class': 'form-control'})

    profile_form = ProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(request.user)
    success_message = None

    if request.method == 'POST':
        if 'profile_submit' in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                success_message = "Profile updated successfully!"
        elif 'password_submit' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                success_message = "Password changed successfully!"

    context = {
        'user': request.user,
        'profile_form': profile_form,
        'password_form': password_form,
        'success_message': success_message,
    }

    return render(request, 'core/settings_profile.html', context)


@login_required
def settings_general_view(request):
    """General system settings view (admin only)"""
    if not request.user.is_staff:
        return redirect('settings')

    # Import the SystemConfiguration model from user_settings if it exists
    try:
        from django.apps import apps
        SystemConfiguration = apps.get_model('user_settings', 'SystemConfiguration')

        configs = SystemConfiguration.objects.all().order_by('key')
        success_message = None

        if request.method == 'POST':
            # Handle config updates
            for config in configs:
                new_value = request.POST.get(f'config_{config.id}')
                if new_value is not None and new_value != config.value:
                    config.value = new_value
                    config.updated_by = request.user
                    config.save()
            success_message = "System configuration updated successfully!"

    except Exception:
        # If user_settings app isn't available, show basic info
        configs = []
        success_message = None

    # Add system stats
    total_users = User.objects.count()
    from core.models import AppRegistry
    active_apps = AppRegistry.objects.filter(is_active=True).count()

    context = {
        'user': request.user,
        'configs': configs,
        'success_message': success_message,
        'total_users': total_users,
        'active_apps': active_apps,
    }

    return render(request, 'core/settings_general.html', context)


@login_required
def settings_voip_view(request):
    """VoIP SIP credentials settings - delegates to calls app"""
    from apps.calls.views import sip_settings_view
    return sip_settings_view(request)
