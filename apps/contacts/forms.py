from django import forms
from .models import Company, Contact


_COMPANY_LANG_CHOICES = [('', 'System Default'), ('en', 'English'), ('ka', 'Georgian')]
_CONTACT_LANG_CHOICES = [('', 'Company Default'), ('en', 'English'), ('ka', 'Georgian')]


class CompanyForm(forms.ModelForm):
    preferred_language = forms.ChoiceField(
        choices=_COMPANY_LANG_CHOICES,
        widget=forms.RadioSelect(),
        required=False,
        label="Preferred Pitch Language",
    )

    class Meta:
        model = Company
        fields = [
            'contact_type',
            'preferred_language',
            'legal_id', 'legal_name', 'brand_name',
            'company_phone', 'company_mobile', 'company_email',
            'industry', 'category',
        ]
        widgets = {
            'contact_type': forms.RadioSelect(),
            'legal_id': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'industry': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ContactForm(forms.ModelForm):
    preferred_language = forms.ChoiceField(
        choices=_CONTACT_LANG_CHOICES,
        widget=forms.RadioSelect(),
        required=False,
        label="Preferred Pitch Language",
    )

    class Meta:
        model = Contact
        fields = ['name', 'position', 'email', 'phone', 'mobile', 'preferred_language']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
        }