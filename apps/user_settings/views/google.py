"""
Transcription settings — ElevenLabs API key, default keywords, and
per-team keyword vocabulary.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import path

from apps.user_settings.models.general import SystemConfiguration

SETTING_KEY = 'elevenlabs_api_key'
KEYWORDS_KEY_EN = 'stt_keywords_en'
KEYWORDS_KEY_KA = 'stt_keywords_ka'


def _require_admin(request):
    return request.user.is_staff or getattr(request.user, 'is_owner', False)


@login_required
def google_credentials_view(request):
    if not _require_admin(request):
        messages.error(request, "You don't have permission to access Transcription settings.")
        return redirect('settings:home')

    from apps.crm.models.sales_team import SalesTeam

    current_key = SystemConfiguration.get_setting(SETTING_KEY) or ''
    status = 'configured' if current_key else 'not_configured'
    error = None

    if request.method == 'POST':
        action = request.POST.get('action', 'save_key')

        if action == 'clear_key':
            SystemConfiguration.objects.filter(key=SETTING_KEY).delete()
            messages.success(request, 'ElevenLabs API key removed.')
            return redirect('settings:google:credentials')

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
                return redirect('settings:google:credentials')

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
            return redirect('settings:google:credentials')

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
            return redirect('settings:google:credentials')

    teams = SalesTeam.objects.filter(is_active=True).order_by('name')

    context = {
        'current_section': 'google',
        'current_page': 'credentials',
        'api_key': current_key,
        'status': status,
        'error': error,
        'stt_keywords_en': SystemConfiguration.get_setting(KEYWORDS_KEY_EN) or '',
        'stt_keywords_ka': SystemConfiguration.get_setting(KEYWORDS_KEY_KA) or '',
        'teams': teams,
    }
    return render(request, 'settings/google/credentials.html', context)


google_urls = [
    path('credentials/', google_credentials_view, name='credentials'),
]
