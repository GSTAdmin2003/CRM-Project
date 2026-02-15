from django import forms
from .models import Activity, ActivityType
from apps.crm.models import Lead
from core.models import User


class ActivityTypeForm(forms.ModelForm):
    """Form for creating/editing activity types"""

    class Meta:
        model = ActivityType
        fields = ['name', 'icon', 'color', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'e.g., Phone Call, Meeting'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'e.g., fas fa-phone, fas fa-calendar'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-input h-10 w-20 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'
            }),
        }


class ActivityForm(forms.ModelForm):
    """Form for creating/editing activities"""

    class Meta:
        model = Activity
        fields = ['activity_type', 'title', 'description', 'scheduled_date', 'lead', 'assigned_to', 'status', 'outcome']
        labels = {
            'lead': 'Opportunity',
        }
        widgets = {
            'activity_type': forms.Select(attrs={
                'class': 'form-select block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'Brief description of the activity'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Additional details or notes'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'lead': forms.Select(attrs={
                'class': 'form-select block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'outcome': forms.Textarea(attrs={
                'class': 'form-textarea block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'What was the result of this activity?'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        lead_id = kwargs.pop('lead_id', None)
        super().__init__(*args, **kwargs)

        # Filter activity types to only active ones
        self.fields['activity_type'].queryset = ActivityType.objects.filter(is_active=True)

        # Filter leads based on user permissions
        if self.user:
            if self.user.is_sales_executive():
                accessible_leads = Lead.objects.all()
            elif self.user.is_sales_manager() and self.user.sales_team:
                team_members = self.user.sales_team.get_team_members()
                accessible_leads = Lead.objects.filter(assigned_to__in=team_members)
            else:
                accessible_leads = Lead.objects.filter(assigned_to=self.user)

            self.fields['lead'].queryset = accessible_leads.order_by('-created_at')

            # Filter assigned_to based on user permissions
            if self.user.is_sales_executive():
                sales_users = User.objects.filter(
                    user_roles__role__name__in=['Sales Rep', 'Sales Manager', 'Sales Executive'],
                    is_active=True
                ).distinct()
                self.fields['assigned_to'].queryset = sales_users
            elif self.user.is_sales_manager() and self.user.sales_team:
                team_members = self.user.sales_team.get_team_members()
                self.fields['assigned_to'].queryset = team_members
            else:
                self.fields['assigned_to'].queryset = User.objects.filter(id=self.user.id)
                self.fields['assigned_to'].initial = self.user

        # Pre-fill lead if provided
        if lead_id and not self.instance.pk:
            try:
                lead = Lead.objects.get(id=lead_id)
                self.fields['lead'].initial = lead
            except Lead.DoesNotExist:
                pass

        # Pre-fill assigned_to with current user by default
        if not self.instance.pk and self.user:
            self.fields['assigned_to'].initial = self.user

        # Make outcome not required (only required when completing)
        self.fields['outcome'].required = False

    def save(self, commit=True):
        activity = super().save(commit=False)

        # Set created_by on new activities
        if not activity.pk and self.user:
            activity.created_by = self.user

        # Set completed_at when status changes to completed
        if activity.status == 'completed' and not activity.completed_at:
            from django.utils import timezone
            activity.completed_at = timezone.now()

        if commit:
            activity.save()

        return activity
