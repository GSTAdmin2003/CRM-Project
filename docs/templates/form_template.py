"""
Django Form Template
Follow this pattern when creating forms for the CRM system
"""

from django import forms
from .models import YourModel


class YourModelForm(forms.ModelForm):
    """
    Form for creating/editing YourModel instances
    """

    class Meta:
        model = YourModel
        fields = [
            'field1',
            'field2',
            'field3',
            'field4',
            'field5',
            'status',  # If using status bar
        ]

        # Configure widgets with proper CSS classes
        widgets = {
            # Text Input
            'field1': forms.TextInput(attrs={
                'class': 'form-field',
                'placeholder': 'Enter field1'
            }),

            # Email Input
            'email': forms.EmailInput(attrs={
                'class': 'form-field',
                'placeholder': 'email@example.com'
            }),

            # Select/Dropdown
            'field2': forms.Select(attrs={
                'class': 'form-field'
            }),

            # Textarea
            'field3': forms.Textarea(attrs={
                'class': 'form-field form-textarea',
                'rows': 4,
                'placeholder': 'Enter description'
            }),

            # Date Input
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-field',
                'type': 'date'
            }),

            # DateTime Input
            'scheduled_datetime': forms.DateTimeInput(attrs={
                'class': 'form-field',
                'type': 'datetime-local'
            }),

            # Number Input
            'amount': forms.NumberInput(attrs={
                'class': 'form-field',
                'step': '0.01',
                'min': '0'
            }),

            # Checkbox (doesn't need form-field class)
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'
            }),

            # Multiple Select
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-field',
                'size': '5'
            }),

            # Hidden Status Field (for status bar)
            'status': forms.HiddenInput(),
        }

        # Optional: Custom labels
        labels = {
            'field1': 'Field 1 Label',
            'field2': 'Field 2 Label',
        }

        # Optional: Help texts
        help_texts = {
            'field3': 'This is a helpful description of the field',
        }

    def __init__(self, *args, **kwargs):
        """
        Customize form initialization
        Use this for:
        - Dynamic queryset filtering
        - Setting initial values
        - User-based field customization
        """
        # Extract custom kwargs
        user = kwargs.pop('user', None)
        lead_id = kwargs.pop('lead_id', None)

        super().__init__(*args, **kwargs)

        # Example: Filter related field based on user permissions
        if user:
            if user.is_sales_rep():
                # Sales reps can only assign to themselves
                self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
                self.fields['assigned_to'].initial = user
            elif user.is_sales_manager() and user.sales_team:
                # Managers can assign to their team members
                team_members = user.sales_team.get_team_members()
                self.fields['assigned_to'].queryset = User.objects.filter(id__in=[m.id for m in team_members])
            elif user.is_sales_executive():
                # Executives can assign to anyone
                self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)

        # Example: Pre-fill field based on parameter
        if lead_id:
            self.fields['lead'].initial = lead_id
            self.fields['lead'].widget.attrs['readonly'] = True

        # Example: Make field required conditionally
        if self.instance.pk and self.instance.status == 'completed':
            self.fields['outcome'].required = True

        # Example: Add custom validation message
        self.fields['field1'].error_messages = {
            'required': 'This field is required. Please provide a value.',
            'invalid': 'Please enter a valid value.',
        }

    def clean_field1(self):
        """
        Custom validation for field1
        """
        field1 = self.cleaned_data.get('field1')

        # Example validation
        if field1 and len(field1) < 3:
            raise forms.ValidationError('Field1 must be at least 3 characters long.')

        return field1

    def clean(self):
        """
        Cross-field validation
        """
        cleaned_data = super().clean()

        # Example: Validate field combinations
        field1 = cleaned_data.get('field1')
        field2 = cleaned_data.get('field2')

        if field1 and field2:
            # Add cross-field validation logic
            pass

        return cleaned_data

    def save(self, commit=True):
        """
        Custom save logic
        """
        instance = super().save(commit=False)

        # Example: Auto-fill created_by on new instances
        if not instance.pk and hasattr(self, 'user'):
            instance.created_by = self.user

        # Example: Set timestamp on status change
        if instance.status == 'completed' and not instance.completed_at:
            from django.utils import timezone
            instance.completed_at = timezone.now()

        if commit:
            instance.save()
            # Don't forget to save many-to-many relationships
            self.save_m2m()

        return instance


# Example: Form with custom field
class CustomForm(forms.ModelForm):
    """
    Example form with additional custom fields not in the model
    """

    # Custom field not in model
    confirm_email = forms.EmailField(
        label='Confirm Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-field',
            'placeholder': 'Confirm your email'
        })
    )

    class Meta:
        model = YourModel
        fields = ['email', 'name']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-field'}),
            'name': forms.TextInput(attrs={'class': 'form-field'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')

        if email and confirm_email and email != confirm_email:
            raise forms.ValidationError('Email addresses must match.')

        return cleaned_data


# Example: Simple form without model
class SearchForm(forms.Form):
    """
    Example non-model form for search/filtering
    """

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-field',
            'placeholder': 'Search...'
        })
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-field',
            'type': 'date'
        })
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-field',
            'type': 'date'
        })
    )

    category = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Categories'),
            ('cat1', 'Category 1'),
            ('cat2', 'Category 2'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-field'
        })
    )
