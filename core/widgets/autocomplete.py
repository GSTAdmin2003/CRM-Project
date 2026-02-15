"""
Reusable autocomplete widget and field classes for Django forms.

Provides a generic autocomplete component that can be configured for any model.
"""
from django import forms
from django.urls import reverse


# Registry of models that can be used with autocomplete
AUTOCOMPLETE_REGISTRY = {
    'contacts.Company': {
        'search_fields': ['legal_id', 'legal_name', 'brand_name'],
        'display_field': 'brand_name',  # Falls back to legal_name if empty
        'secondary_field': 'legal_name',
        'id_display_field': 'legal_id',
        'view_url_name': 'contacts:company_detail',
        'allow_create': True,
    },
    'contacts.Contact': {
        'search_fields': ['name', 'email', 'phone'],
        'display_field': 'name',
        'secondary_field': 'email',
        'id_display_field': None,
        'view_url_name': 'contacts:contact_detail',
        'allow_create': False,
    },
    'crm.SalesTeam': {
        'search_fields': ['name', 'description'],
        'display_field': 'name',
        'secondary_field': 'description',
        'id_display_field': None,
        'view_url_name': '',
        'allow_create': False,
        'filter_active': True,  # Only show active teams
    },
    'core.User': {
        'search_fields': ['username', 'first_name', 'last_name', 'email'],
        'display_field': 'get_full_name',  # Method call
        'secondary_field': 'email',
        'id_display_field': 'username',
        'view_url_name': '',
        'allow_create': False,
        'filter_active': True,  # Only show active users
    },
}


class AutocompleteWidget(forms.TextInput):
    """
    Custom widget for text input with autocomplete functionality.

    Renders an input field with data attributes that the JavaScript
    autocomplete component uses to initialize itself. The JS creates
    the wrapper, dropdown, and view button dynamically.
    """

    def __init__(self, model_name, placeholder='', allow_create=None,
                 view_url_name=None, *args, **kwargs):
        """
        Initialize the autocomplete widget.

        Args:
            model_name: The model to search (e.g., 'contacts.Company')
            placeholder: Input placeholder text
            allow_create: Whether to show "Create new" option (overrides registry)
            view_url_name: URL pattern for view button (overrides registry)
        """
        super().__init__(*args, **kwargs)

        self.model_name = model_name
        self.placeholder = placeholder

        # Get config from registry
        config = AUTOCOMPLETE_REGISTRY.get(model_name, {})

        # Use provided values or fall back to registry
        self.allow_create = allow_create if allow_create is not None else config.get('allow_create', False)
        self.view_url_name = view_url_name or config.get('view_url_name', '')

        # Set widget attributes
        self.attrs.update({
            'class': 'form-field autocomplete-input block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
            'placeholder': self.placeholder,
            'autocomplete': 'off',
            'data-autocomplete': 'true',
            'data-model': self.model_name,
            'data-allow-create': 'true' if self.allow_create else 'false',
            'data-view-url-name': self.view_url_name,
        })

    def get_context(self, name, value, attrs):
        """Add autocomplete-specific context for template rendering."""
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'model_name': self.model_name,
            'allow_create': self.allow_create,
            'view_url_name': self.view_url_name,
            'placeholder': self.placeholder,
        })
        return context


class AutocompleteField(forms.CharField):
    """
    Base field class for autocomplete inputs.

    Handles conversion between display value and actual value (ID).
    """
    def __init__(self, model_name, placeholder='', allow_create=None,
                 view_url_name=None, *args, **kwargs):
        """
        Initialize the autocomplete field.

        Args:
            model_name: The model to search (e.g., 'contacts.Company')
            placeholder: Input placeholder text
            allow_create: Whether to show "Create new" option
            view_url_name: URL pattern for view button
        """
        self.model_name = model_name

        # Create widget with configuration
        widget = AutocompleteWidget(
            model_name=model_name,
            placeholder=placeholder,
            allow_create=allow_create,
            view_url_name=view_url_name,
        )

        kwargs.setdefault('widget', widget)
        kwargs.setdefault('max_length', 200)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Clean the input value."""
        if not value:
            return ""
        return value.strip()


def make_autocomplete_field(model_name, placeholder='', allow_create=None,
                            view_url_name=None, **field_kwargs):
    """
    Factory function to create a configured autocomplete field class.

    Args:
        model_name: The model to search (e.g., 'contacts.Company')
        placeholder: Input placeholder text
        allow_create: Whether to show "Create new" option
        view_url_name: URL pattern for view button
        **field_kwargs: Additional kwargs to pass to the field

    Returns:
        A callable that creates an AutocompleteField instance

    Usage:
        company = make_autocomplete_field(
            model_name='contacts.Company',
            placeholder='Type company name...',
        )()
    """
    def create_field(**kwargs):
        merged_kwargs = {**field_kwargs, **kwargs}
        return AutocompleteField(
            model_name=model_name,
            placeholder=placeholder,
            allow_create=allow_create,
            view_url_name=view_url_name,
            **merged_kwargs
        )
    return create_field


# Pre-configured field shortcuts
def CompanyAutocompleteField(**kwargs):
    """
    Pre-configured autocomplete field for Company model.

    Usage:
        company = CompanyAutocompleteField()
    """
    kwargs.setdefault('placeholder', 'Type company name...')
    return AutocompleteField(
        model_name='contacts.Company',
        view_url_name='contacts:company_detail',
        allow_create=True,
        **kwargs
    )


def ContactAutocompleteField(**kwargs):
    """
    Pre-configured autocomplete field for Contact model.

    Usage:
        contact = ContactAutocompleteField()
    """
    kwargs.setdefault('placeholder', 'Type contact name...')
    return AutocompleteField(
        model_name='contacts.Contact',
        view_url_name='contacts:contact_detail',
        allow_create=False,
        **kwargs
    )


def SalesTeamAutocompleteField(**kwargs):
    """
    Pre-configured autocomplete field for SalesTeam model.

    Usage:
        sales_team = SalesTeamAutocompleteField()
    """
    kwargs.setdefault('placeholder', 'Type team name...')
    return AutocompleteField(
        model_name='crm.SalesTeam',
        allow_create=False,
        **kwargs
    )


def UserAutocompleteField(**kwargs):
    """
    Pre-configured autocomplete field for User model.

    Usage:
        assigned_to = UserAutocompleteField()
    """
    kwargs.setdefault('placeholder', 'Type user name...')
    return AutocompleteField(
        model_name='core.User',
        allow_create=False,
        **kwargs
    )
