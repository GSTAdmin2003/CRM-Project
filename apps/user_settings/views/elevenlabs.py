"""
Transcription settings — ElevenLabs API key, default keywords, and
per-team keyword vocabulary.
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import redirect, render
from django.urls import path

from apps.user_settings.models.general import SystemConfiguration

SETTING_KEY = 'elevenlabs_api_key'
KEYWORDS_KEY_EN = 'stt_keywords_en'
KEYWORDS_KEY_KA = 'stt_keywords_ka'
AUTO_TRANSCRIBE_KEY = 'transcription_auto_enabled'


def _require_admin(request):
    return request.user.is_staff or getattr(request.user, 'is_owner', False)


@login_required
def elevenlabs_config_view(request):
    if not _require_admin(request):
        messages.error(request, "You don't have permission to access Transcription settings.")
        return redirect('settings:home')

    current_key = SystemConfiguration.get_setting(SETTING_KEY) or ''
    status = 'configured' if current_key else 'not_configured'
    error = None

    auto_transcribe = SystemConfiguration.get_setting(AUTO_TRANSCRIBE_KEY, False)

    if request.method == 'POST':
        action = request.POST.get('action', 'save_key')

        if action == 'clear_key':
            SystemConfiguration.objects.filter(key=SETTING_KEY).delete()
            messages.success(request, 'ElevenLabs API key removed.')
            return redirect('settings:elevenlabs:config')

        if action == 'save_key':
            raw = request.POST.get('api_key', '').strip()
            if not raw:
                error = 'API key cannot be empty.'
            else:
                SystemConfiguration.set_setting(
                    key=SETTING_KEY,
                    value=raw,
                    description='ElevenLabs API key for Speech-to-Text (Scribe)',
                    data_type='string',
                    user=request.user,
                )
                messages.success(request, 'ElevenLabs API key saved successfully.')
                return redirect('settings:elevenlabs:config')

        if action == 'save_auto_transcribe':
            enabled = request.POST.get('auto_transcribe') == 'on'
            SystemConfiguration.set_setting(
                key=AUTO_TRANSCRIBE_KEY,
                value='true' if enabled else 'false',
                description='Automatically transcribe calls after recording is processed',
                data_type='boolean',
                user=request.user,
            )
            messages.success(
                request,
                'Auto-transcription enabled.' if enabled else 'Auto-transcription disabled.',
            )
            return redirect('settings:elevenlabs:config')

    context = {
        'current_section': 'elevenlabs',
        'current_page': 'config',
        'api_key': current_key,
        'status': status,
        'error': error,
        'auto_transcribe': auto_transcribe,
        'init_data_json': json.dumps(
            {'apiUrls': {'config': '/settings/api/elevenlabs/config/'}},
            cls=DjangoJSONEncoder,
        ),
    }
    return render(request, 'settings/elevenlabs/config.html', context)


@login_required
def elevenlabs_vocabulary_view(request):
    if not _require_admin(request):
        messages.error(request, "You don't have permission to access Transcription settings.")
        return redirect('settings:home')

    from apps.crm.models.sales_team import SalesTeam

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_keywords':
            SystemConfiguration.set_setting(
                key=KEYWORDS_KEY_EN,
                value=request.POST.get('stt_keywords_en', '').strip(),
                description='Default English custom vocabulary keywords for ElevenLabs STT',
                data_type='string',
                user=request.user,
            )
            SystemConfiguration.set_setting(
                key=KEYWORDS_KEY_KA,
                value=request.POST.get('stt_keywords_ka', '').strip(),
                description='Default Georgian custom vocabulary keywords for ElevenLabs STT',
                data_type='string',
                user=request.user,
            )
            messages.success(request, 'Default keywords saved.')
            return redirect('settings:elevenlabs:vocabulary')

        if action == 'save_team_keywords':
            team_id = request.POST.get('team_id')
            try:
                team = SalesTeam.objects.get(pk=team_id)
                team.stt_keywords_en = request.POST.get('team_keywords_en', '').strip()
                team.stt_keywords_ka = request.POST.get('team_keywords_ka', '').strip()
                team.save(update_fields=['stt_keywords_en', 'stt_keywords_ka'])
                messages.success(request, f'Keywords saved for team "{team.name}".')
            except SalesTeam.DoesNotExist:
                messages.error(request, 'Sales team not found.')
            return redirect('settings:elevenlabs:vocabulary')

    teams = SalesTeam.objects.filter(is_active=True).order_by('name')

    context = {
        'current_section': 'elevenlabs',
        'current_page': 'vocabulary',
        'stt_keywords_en': SystemConfiguration.get_setting(KEYWORDS_KEY_EN) or '',
        'stt_keywords_ka': SystemConfiguration.get_setting(KEYWORDS_KEY_KA) or '',
        'teams': teams,
        'init_data_json': json.dumps(
            {'apiUrls': {'vocabulary': '/settings/api/elevenlabs/vocabulary/'}},
            cls=DjangoJSONEncoder,
        ),
    }
    return render(request, 'settings/elevenlabs/vocabulary.html', context)


ANTHROPIC_KEY = 'anthropic_api_key'
AI_AUTO_KEY = 'ai_analysis_auto_enabled'
AI_DEFAULT_DAYS_KEY = 'ai_activity_default_days'


@login_required
def ai_config_view(request):
    """Settings for Claude AI call analysis: API key and auto-enable toggle."""
    if not _require_admin(request):
        messages.error(request, "You don't have permission to access AI Analysis settings.")
        return redirect('settings:home')

    current_key = SystemConfiguration.get_setting(ANTHROPIC_KEY) or ''
    auto_enabled = SystemConfiguration.get_setting(AI_AUTO_KEY, False)
    default_days = int(SystemConfiguration.get_setting(AI_DEFAULT_DAYS_KEY, 1) or 1)
    error = None

    if request.method == 'POST':
        action = request.POST.get('action', 'save_key')

        if action == 'clear_key':
            SystemConfiguration.objects.filter(key=ANTHROPIC_KEY).delete()
            messages.success(request, 'Anthropic API key removed.')
            return redirect('settings:elevenlabs:ai_config')

        if action == 'save_key':
            raw = request.POST.get('api_key', '').strip()
            if not raw:
                error = 'API key cannot be empty.'
            else:
                SystemConfiguration.set_setting(
                    key=ANTHROPIC_KEY,
                    value=raw,
                    description='Anthropic API key for Claude AI call analysis',
                    data_type='string',
                    user=request.user,
                )
                messages.success(request, 'Anthropic API key saved.')
                return redirect('settings:elevenlabs:ai_config')

        if action == 'save_auto_enabled':
            enabled = request.POST.get('auto_enabled') == 'on'
            SystemConfiguration.set_setting(
                key=AI_AUTO_KEY,
                value='true' if enabled else 'false',
                description='Automatically run Claude AI analysis after transcription completes',
                data_type='boolean',
                user=request.user,
            )
            messages.success(
                request,
                'Auto AI analysis enabled.' if enabled else 'Auto AI analysis disabled.',
            )
            return redirect('settings:elevenlabs:ai_config')

        if action == 'save_default_days':
            try:
                days = max(0, int(request.POST.get('default_days', 1)))
            except (ValueError, TypeError):
                days = 1
            SystemConfiguration.set_setting(
                key=AI_DEFAULT_DAYS_KEY,
                value=str(days),
                description='Default scheduled interval (days from today) for AI-created activities',
                data_type='integer',
                user=request.user,
            )
            messages.success(request, f'Default interval set to {days} day(s) from today.')
            return redirect('settings:elevenlabs:ai_config')

    context = {
        'current_section': 'elevenlabs',
        'current_page': 'ai_config',
        'api_key': current_key,
        'status': 'configured' if current_key else 'not_configured',
        'error': error,
        'auto_enabled': auto_enabled,
        'default_days': default_days,
        'init_data_json': json.dumps(
            {'apiUrls': {'aiConfig': '/settings/api/elevenlabs/ai/'}},
            cls=DjangoJSONEncoder,
        ),
    }
    return render(request, 'settings/elevenlabs/ai_config.html', context)


@login_required
def team_products_view(request):
    """Edit product descriptions for each sales team (used as AI analysis context)."""
    if not _require_admin(request):
        messages.error(request, "You don't have permission to access AI Analysis settings.")
        return redirect('settings:home')

    from apps.crm.models.sales_team import SalesTeam

    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        try:
            team = SalesTeam.objects.get(pk=team_id)
            team.product_description = request.POST.get('product_description', '').strip()
            team.save(update_fields=['product_description', 'updated_at'])
            messages.success(request, f'Product description saved for team "{team.name}".')
        except SalesTeam.DoesNotExist:
            messages.error(request, 'Sales team not found.')
        return redirect('settings:elevenlabs:team_products')

    teams = SalesTeam.objects.filter(is_active=True).order_by('name')
    context = {
        'current_section': 'elevenlabs',
        'current_page': 'team_products',
        'teams': teams,
        'init_data_json': json.dumps(
            {'apiUrls': {'teamProducts': '/settings/api/elevenlabs/team-products/'}},
            cls=DjangoJSONEncoder,
        ),
    }
    return render(request, 'settings/elevenlabs/team_products.html', context)


elevenlabs_urls = [
    path('config/', elevenlabs_config_view, name='config'),
    path('vocabulary/', elevenlabs_vocabulary_view, name='vocabulary'),
    path('team-products/', team_products_view, name='team_products'),
]
