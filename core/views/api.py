"""
API views for core functionality.

Provides generic endpoints for autocomplete search across registered models.
"""
import json
from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from core.widgets.autocomplete import AUTOCOMPLETE_REGISTRY


def get_display_value(item, field_name):
    """
    Get a display value from an item, handling both attributes and methods.

    Args:
        item: The model instance
        field_name: The field or method name

    Returns:
        The string value
    """
    if not field_name:
        return ''

    attr = getattr(item, field_name, None)
    if attr is None:
        return ''

    # If it's callable (a method), call it
    if callable(attr):
        try:
            return str(attr()) or ''
        except Exception:
            return ''

    return str(attr) or ''


@login_required
@require_GET
def api_autocomplete_search(request):
    """
    Generic autocomplete search endpoint.

    Accepts:
        model: Model name from registry (e.g., 'contacts.Company')
        q: Search query string
        limit: Maximum number of results (default 10, max 50)

    Returns:
        JSON response with:
        - results: List of matching items with id, display, secondary, id_field
        - config: Model configuration (allow_create, view_url_name)
    """
    model_name = request.GET.get('model', '')
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 50)

    # Validate model is in registry
    if model_name not in AUTOCOMPLETE_REGISTRY:
        return JsonResponse({
            'error': f'Model "{model_name}" not found in autocomplete registry',
            'results': [],
            'config': {},
        }, status=400)

    config = AUTOCOMPLETE_REGISTRY[model_name]

    # Resolve actual model class (may differ from registry key via model_class override)
    actual_model_name = config.get('model_class', model_name)
    try:
        app_label, model_class_name = actual_model_name.split('.')
        Model = apps.get_model(app_label, model_class_name)
    except (ValueError, LookupError) as e:
        return JsonResponse({
            'error': f'Invalid model: {str(e)}',
            'results': [],
            'config': {},
        }, status=400)

    # Build search query
    search_fields = config.get('search_fields', [])
    display_field = config.get('display_field', 'name')
    secondary_field = config.get('secondary_field')
    id_display_field = config.get('id_display_field')

    # Start with base queryset, applying any mandatory filters from registry
    queryset = Model.objects.all()
    if config.get('filter_kwargs'):
        queryset = queryset.filter(**config['filter_kwargs'])

    # Apply filter_active if configured
    if config.get('filter_active'):
        if hasattr(Model, 'is_active'):
            queryset = queryset.filter(is_active=True)

    # Build Q objects for search
    if query:
        q_objects = Q()
        for field in search_fields:
            q_objects |= Q(**{f'{field}__icontains': query})
        queryset = queryset.filter(q_objects)

    # Apply ordering and limit
    queryset = queryset[:limit]

    # Build results
    results = []
    for item in queryset:
        # Get display value (with fallback) - handle methods
        display = get_display_value(item, display_field)
        if not display and secondary_field:
            display = get_display_value(item, secondary_field)

        # Get secondary value
        secondary = get_display_value(item, secondary_field) if secondary_field else ''

        # Get ID display field (e.g., legal_id for companies, username for users)
        id_field_value = get_display_value(item, id_display_field) if id_display_field else ''

        results.append({
            'id': item.pk,
            'display': display,
            'secondary': secondary,
            'id_field': id_field_value,
        })

    # Build view URL pattern for JavaScript to use
    view_url_pattern = ''
    view_url_name = config.get('view_url_name', '')
    if view_url_name:
        # Generate URL pattern with placeholder for ID
        try:
            # Try to reverse with a placeholder ID to get the pattern
            view_url_pattern = reverse(view_url_name, kwargs={'pk': 0})
            # Replace the placeholder with {id} for JS to use
            view_url_pattern = view_url_pattern.replace('/0/', '/{id}/')
        except Exception:
            view_url_pattern = ''

    return JsonResponse({
        'results': results,
        'config': {
            'allow_create': config.get('allow_create', False),
            'view_url_name': view_url_name,
            'view_url_pattern': view_url_pattern,
        },
    })
