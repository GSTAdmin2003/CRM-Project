from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import UserPreferences, SystemConfiguration
from core.models import Role
from apps.crm.models import SalesTeam

User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = ['theme', 'language', 'timezone', 'notifications_email', 'notifications_browser']
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.RadioSelect(),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'notifications_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notifications_browser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class SystemConfigurationForm(forms.ModelForm):
    class Meta:
        model = SystemConfiguration
        fields = ['value', 'description']
        widgets = {
            'value': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


_INPUT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500'


def get_whatsapp_config_form():
    """Return WhatsAppConfigForm class (imported lazily after app registry is ready)."""
    from apps.messaging.models import WhatsAppConfig

    class WhatsAppConfigForm(forms.ModelForm):
        class Meta:
            model = WhatsAppConfig
            fields = [
                'access_token', 'phone_number_id', 'app_secret',
                'webhook_verify_token', 'app_id', 'waba_id', 'is_active',
            ]
            widgets = {
                'access_token': forms.Textarea(attrs={
                    'class': _INPUT_CLASS, 'rows': 3,
                    'placeholder': 'EAAxxxxxxxxx...', 'autocomplete': 'off',
                }),
                'phone_number_id': forms.TextInput(attrs={
                    'class': _INPUT_CLASS, 'placeholder': '123456789012345',
                }),
                'app_secret': forms.PasswordInput(render_value=True, attrs={
                    'class': _INPUT_CLASS,
                    'placeholder': 'Leave blank to keep current value',
                    'autocomplete': 'new-password',
                }),
                'webhook_verify_token': forms.TextInput(attrs={
                    'class': _INPUT_CLASS, 'placeholder': 'crm-webhook-token',
                }),
                'app_id': forms.TextInput(attrs={
                    'class': _INPUT_CLASS, 'placeholder': '123456789012345',
                }),
                'waba_id': forms.TextInput(attrs={
                    'class': _INPUT_CLASS, 'placeholder': '123456789012345',
                }),
                'is_active': forms.CheckboxInput(
                    attrs={'class': 'h-4 w-4 text-green-600 border-gray-300 rounded'}
                ),
            }

    return WhatsAppConfigForm


def get_whatsapp_template_form():
    """Return WhatsAppTemplateForm class (imported lazily after app registry is ready)."""
    from apps.messaging.models import WhatsAppTemplate

    class WhatsAppTemplateForm(forms.ModelForm):
        variable_names_text = forms.CharField(
            label="Variable Names (comma-separated)",
            required=False,
            widget=forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'Customer Name, Date, Amount',
            }),
            help_text="Ordered labels for each {{1}}, {{2}} placeholder. Leave blank if no variables.",
        )

        class Meta:
            model = WhatsAppTemplate
            fields = ['name', 'display_name', 'language', 'body_preview', 'is_active']
            widgets = {
                'name': forms.TextInput(attrs={
                    'class': _INPUT_CLASS,
                    'placeholder': 'hello_world',
                }),
                'display_name': forms.TextInput(attrs={
                    'class': _INPUT_CLASS,
                    'placeholder': 'Hello World Greeting',
                }),
                'language': forms.TextInput(attrs={
                    'class': _INPUT_CLASS,
                    'placeholder': 'en_US',
                }),
                'body_preview': forms.Textarea(attrs={
                    'class': _INPUT_CLASS,
                    'rows': 4,
                    'placeholder': 'Hello {{1}}, your appointment is on {{2}}.',
                }),
                'is_active': forms.CheckboxInput(
                    attrs={'class': 'h-4 w-4 text-green-600 border-gray-300 rounded'}
                ),
            }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.instance and self.instance.pk and self.instance.variable_names:
                self.initial['variable_names_text'] = ', '.join(self.instance.variable_names)

        def clean_variable_names_text(self):
            raw = self.cleaned_data.get('variable_names_text', '')
            if not raw.strip():
                return []
            return [v.strip() for v in raw.split(',') if v.strip()]

        def save(self, commit=True):
            instance = super().save(commit=False)
            instance.variable_names = self.cleaned_data.get('variable_names_text', [])
            if commit:
                instance.save()
            return instance

    return WhatsAppTemplateForm


def get_sales_team_pitch_form():
    """Return SalesTeamPitchForm class (imported lazily after app registry is ready)."""
    from apps.crm.models import SalesTeam

    class SalesTeamPitchForm(forms.ModelForm):
        class Meta:
            model = SalesTeam
            fields = ['pitch_pdf']
            widgets = {
                'pitch_pdf': forms.FileInput(attrs={'class': _INPUT_CLASS, 'accept': '.pdf'}),
            }

    return SalesTeamPitchForm


_SELECT_CLASS = _INPUT_CLASS
_CHECK_CLASS = 'h-4 w-4 text-indigo-600 border-gray-300 rounded'


class UserCreateForm(forms.ModelForm):
    """Form for creating a new CRM user account."""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': _INPUT_CLASS}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': _INPUT_CLASS}),
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Roles',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'sales_team', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'first_name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': _INPUT_CLASS}),
            'sales_team': forms.Select(attrs={'class': _SELECT_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECK_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sales_team'].queryset = SalesTeam.objects.filter(is_active=True)
        self.fields['sales_team'].empty_label = '— No Team —'
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['sales_team'].required = False

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Passwords do not match.')
        if len(p1) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return p2

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing an existing user — no password change here."""

    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Roles',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'sales_team', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': _INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': _INPUT_CLASS}),
            'sales_team': forms.Select(attrs={'class': _SELECT_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECK_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sales_team'].queryset = SalesTeam.objects.filter(is_active=True)
        self.fields['sales_team'].empty_label = '— No Team —'
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['sales_team'].required = False
        # Pre-select the user's current roles
        if self.instance.pk:
            self.initial['roles'] = self.instance.user_roles.values_list('role_id', flat=True)