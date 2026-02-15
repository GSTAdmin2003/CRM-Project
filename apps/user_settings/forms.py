from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model
from .models import UserPreferences, SystemConfiguration, SIPSettings

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
            'language': forms.Select(attrs={'class': 'form-select'}),
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


class SIPSettingsForm(forms.ModelForm):
    """Form for SIP credentials configuration"""

    class Meta:
        model = SIPSettings
        fields = ['server_ip', 'server_port', 'username', 'password', 'caller_id', 'is_active']
        widgets = {
            'server_ip': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., sip.provider.com or 192.168.1.100'
            }),
            'server_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '5060'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your SIP username'
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your SIP password',
                'autocomplete': 'new-password'
            }),
            'caller_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., +1234567890'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing, show placeholder for password
        if self.instance and self.instance.pk:
            self.fields['password'].widget.attrs['placeholder'] = 'Leave blank to keep current password'
            self.fields['password'].required = False

    def clean_password(self):
        password = self.cleaned_data.get('password')
        # If no new password provided and editing existing, keep old password
        if not password and self.instance and self.instance.pk:
            return self.instance.password
        return password