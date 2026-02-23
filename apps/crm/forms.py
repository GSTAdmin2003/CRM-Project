from django import forms
from django.contrib.auth import get_user_model
from .models import Lead, LeadStage, SalesTeam
from apps.contacts.models import Company, Contact
from core.widgets.autocomplete import (
    CompanyAutocompleteField,
    SalesTeamAutocompleteField,
    UserAutocompleteField,
)

User = get_user_model()


class LeadForm(forms.ModelForm):
    company = CompanyAutocompleteField()
    assigned_to = UserAutocompleteField(required=False)
    sales_team = SalesTeamAutocompleteField(required=False)

    class Meta:
        model = Lead
        fields = [
            'title', 'full_name', 'email', 'phone',
            'position', 'stage', 'estimated_value',
            'probability', 'expected_close_date',
            'message', 'status', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'full_name': forms.TextInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'email': forms.EmailInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'phone': forms.TextInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'position': forms.TextInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'stage': forms.Select(attrs={'class': 'form-select block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'estimated_value': forms.NumberInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500', 'step': '0.01'}),
            'probability': forms.NumberInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500', 'min': '0', 'max': '100'}),
            'expected_close_date': forms.DateInput(attrs={'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500', 'type': 'date'}),
            'message': forms.Textarea(attrs={'class': 'form-field form-textarea', 'rows': 4, 'placeholder': 'Lead message or inquiry...'}),
            'status': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'class': 'form-textarea block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Store user for company field
        self._form_user = self.user

        # Store the selected contact ID from POST data for persistence
        if self.data:
            self.selected_contact_id = self.data.get('selected_contact_id', '')
        else:
            # For existing leads, use the lead's contact
            self.selected_contact_id = str(self.instance.contact.id) if self.instance.pk and self.instance.contact else ''

        # Filter stages based on user's team
        user_team = self.user.sales_team if self.user else None
        self.fields['stage'].queryset = LeadStage.get_stages_for_team(user_team)

        # Set initial value for assigned_to autocomplete field
        if self.instance.pk and self.instance.assigned_to:
            self.fields['assigned_to'].initial = self.instance.assigned_to.get_full_name() or self.instance.assigned_to.username
        elif self.user and not self.user.is_sales_executive() and not self.user.is_sales_manager():
            # Sales reps default to themselves
            self.fields['assigned_to'].initial = self.user.get_full_name() or self.user.username

        # Make some fields optional for better UX, but company is required
        self.fields['company'].required = True
        self.fields['full_name'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['position'].required = False
        self.fields['expected_close_date'].required = False
        self.fields['message'].required = False
        self.fields['status'].required = False

        # Determine lead_type context for field requirements
        is_lead_type = (
            (self.instance.pk and self.instance.lead_type == Lead.TYPE_LEAD)
            or self.data.get('lead_type') == Lead.TYPE_LEAD
            or getattr(self, '_lead_type', None) == Lead.TYPE_LEAD
        )
        self.fields['title'].required = not is_lead_type
        self.fields['stage'].required = not is_lead_type

        # Set default status for new incoming leads
        if is_lead_type and not self.instance.pk:
            self.fields['status'].initial = 'new'

        # Set initial values for sales_team autocomplete
        if self.instance.pk and self.instance.sales_team:
            self.fields['sales_team'].initial = self.instance.sales_team.name

        # Set default stage if not editing (opportunity only)
        if not self.instance.pk and not is_lead_type:
            user_team = self.user.sales_team if self.user else None
            default_stage = LeadStage.get_default_stage_for_team(user_team)
            if default_stage:
                self.fields['stage'].initial = default_stage
        elif self.instance.pk:
            # For existing leads, set the company name in the text field
            if self.instance.company:
                self.fields['company'].initial = self.instance.company.legal_name
    
    def save(self, commit=True):
        lead = super().save(commit=False)

        # Handle company creation/assignment
        company_name = self.cleaned_data.get('company')
        if company_name:
            company = self._get_or_create_company(company_name)
            lead.company = company
            # Also set the company_name field for backward compatibility
            lead.company_name = company.legal_name if company else company_name

        # Handle assigned_to from autocomplete
        assigned_to_id = self.data.get('assigned_to_id') if self.data else None
        if assigned_to_id and assigned_to_id.strip():
            try:
                lead.assigned_to = User.objects.get(id=int(assigned_to_id))
            except (User.DoesNotExist, ValueError):
                pass
        elif self.user and not self.user.is_sales_executive() and not self.user.is_sales_manager():
            # Default to current user for sales reps
            lead.assigned_to = self.user

        # Handle sales_team from autocomplete
        sales_team_id = self.data.get('sales_team_id') if self.data else None
        if sales_team_id and sales_team_id.strip():
            try:
                lead.sales_team = SalesTeam.objects.get(id=int(sales_team_id))
            except (SalesTeam.DoesNotExist, ValueError):
                pass

        # Set lead_type if provided
        if getattr(self, '_lead_type', None):
            lead.lead_type = self._lead_type

        if not lead.pk and self.user:
            lead.created_by = self.user

            # Auto-assign sales team
            if not lead.sales_team and lead.assigned_to and lead.assigned_to.sales_team:
                lead.sales_team = lead.assigned_to.sales_team

        if commit:
            lead.save()
            # Handle contact selection or creation
            self._handle_contact_assignment(lead)

        return lead
    
    def _get_or_create_company(self, company_input):
        """Get existing company or create new one based on input"""
        if not company_input:
            return None
        
        company_input = company_input.strip()
        
        # Check if it's an ID (from autocomplete selection)
        if company_input.isdigit():
            try:
                return Company.objects.get(id=int(company_input))
            except Company.DoesNotExist:
                pass
        
        # Try to find existing company by name (case insensitive)
        try:
            return Company.objects.get(legal_name__iexact=company_input)
        except Company.DoesNotExist:
            # Create new company
            return Company.objects.create(
                legal_name=company_input,
                legal_id=f'AUTO-{company_input.upper()[:10]}',
                created_by=self.user
            )
    
    def _handle_contact_assignment(self, lead):
        """Handle contact selection or creation based on form data"""
        # Get selected contact ID from form data (passed via hidden field)
        selected_contact_id = self.data.get('selected_contact_id')
        contact_mode = self.data.get('contact_mode')

        if selected_contact_id and selected_contact_id.strip():
            # Contact was selected from existing contacts
            try:
                contact = Contact.objects.get(id=int(selected_contact_id), company=lead.company)
                lead.contact = contact
                lead.save(update_fields=['contact'])

                # Update contact with edited information from form fields
                contact_updated = False
                if lead.full_name and lead.full_name != contact.name:
                    contact.name = lead.full_name
                    contact_updated = True
                if lead.email and lead.email != contact.email:
                    contact.email = lead.email
                    contact_updated = True
                if lead.phone and lead.phone != contact.phone and lead.phone != contact.mobile:
                    contact.phone = lead.phone
                    contact.mobile = lead.phone
                    contact_updated = True
                if lead.position and lead.position != contact.position:
                    contact.position = lead.position
                    contact_updated = True

                # Save contact if any fields were updated
                if contact_updated:
                    contact.save()

                # Also update lead fields with contact info if they're empty
                if not lead.full_name and contact.name:
                    lead.full_name = contact.name
                if not lead.email and contact.email:
                    lead.email = contact.email
                if not lead.phone and (contact.phone or contact.mobile):
                    lead.phone = contact.phone or contact.mobile
                if not lead.position and contact.position:
                    lead.position = contact.position

                lead.save()

            except (Contact.DoesNotExist, ValueError):
                # Contact not found or invalid ID, proceed with creation if data provided
                self._create_or_update_contact(lead, contact_mode)
        else:
            # No contact selected, create/update contact if data provided
            self._create_or_update_contact(lead, contact_mode)

    def _create_or_update_contact(self, lead, contact_mode):
        """Create or update contact based on lead data"""
        # Only create/update contact if we have both name and email
        if lead.company and lead.email and (lead.full_name or (lead.first_name and lead.last_name)):
            contact_name = lead.full_name or f"{lead.first_name} {lead.last_name}".strip()

            # Check if this is a create mode (new contact being created)
            if contact_mode == 'create':
                # Create a new contact
                contact = Contact.objects.create(
                    company=lead.company,
                    name=contact_name,
                    email=lead.email,
                    position=lead.position or '',
                    phone=lead.phone or '',
                    mobile=lead.phone or '',
                )

                # Assign to lead
                lead.contact = contact
                lead.save(update_fields=['contact'])

                # Set as favorite contact if company doesn't have one
                if not lead.company.favorite_contact:
                    lead.company.favorite_contact = contact
                    lead.company.save(update_fields=['favorite_contact'])

            else:
                # Update existing contact or create if doesn't exist (backward compatibility)
                contact, created = Contact.objects.get_or_create(
                    company=lead.company,
                    email=lead.email,
                    defaults={
                        'name': contact_name,
                        'position': lead.position or '',
                        'phone': lead.phone or '',
                        'mobile': lead.phone or '',
                    }
                )

                # Update existing contact if not created
                if not created:
                    contact.name = contact_name
                    if lead.position:
                        contact.position = lead.position
                    if lead.phone:
                        contact.phone = lead.phone
                        contact.mobile = lead.phone
                    contact.save()

                # Assign to lead
                lead.contact = contact
                lead.save(update_fields=['contact'])

            # Update company contact info if not already set
            if lead.company and not lead.company.company_email and lead.email:
                lead.company.company_email = lead.email
                lead.company.save(update_fields=['company_email'])

