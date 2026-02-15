from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Call, CallRecording, CallLog, SIPSettings
from .ari_client import ari_client
import logging

logger = logging.getLogger(__name__)


@login_required
def call_list(request):
    """Display list of all calls"""
    calls = Call.objects.select_related(
        'contact', 'opportunity', 'user', 'recording'
    ).prefetch_related('contact__company')

    # Filter by direction
    direction = request.GET.get('direction')
    if direction in ['inbound', 'outbound']:
        calls = calls.filter(direction=direction)

    # Filter by status
    status = request.GET.get('status')
    if status:
        calls = calls.filter(status=status)

    # Filter by user
    user_filter = request.GET.get('user')
    if user_filter == 'me':
        calls = calls.filter(user=request.user)

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        calls = calls.filter(
            Q(from_number__icontains=search) |
            Q(to_number__icontains=search) |
            Q(contact__name__icontains=search) |
            Q(opportunity__title__icontains=search)
        )

    # Pagination
    paginator = Paginator(calls, 25)
    page = request.GET.get('page', 1)
    calls = paginator.get_page(page)

    context = {
        'calls': calls,
        'direction_filter': direction,
        'status_filter': status,
        'user_filter': user_filter,
        'search': search,
    }
    return render(request, 'calls/call_list.html', context)


@login_required
def call_detail(request, pk):
    """Display call details"""
    call = get_object_or_404(
        Call.objects.select_related('contact', 'opportunity', 'user', 'recording'),
        pk=pk
    )
    logs = call.logs.order_by('timestamp')

    context = {
        'call': call,
        'logs': logs,
    }
    return render(request, 'calls/call_detail.html', context)


@login_required
def dialpad(request):
    """Display dialpad for making calls"""
    # Get recent contacts for quick dial
    from apps.contacts.models import Contact
    recent_contacts = Contact.objects.all()[:10]

    context = {
        'recent_contacts': recent_contacts,
    }
    return render(request, 'calls/dialpad.html', context)


@login_required
@require_POST
def initiate_call(request):
    """Initiate an outbound call via AJAX"""
    to_number = request.POST.get('to_number', '').strip()
    contact_id = request.POST.get('contact_id')
    opportunity_id = request.POST.get('opportunity_id')

    if not to_number:
        return JsonResponse({'error': 'Phone number required'}, status=400)

    # Clean phone number - remove spaces, dashes, etc.
    to_number = ''.join(c for c in to_number if c.isdigit() or c == '+')

    try:
        # Get user's extension (default to 100 if not set)
        from_ext = getattr(request.user, 'extension', None) or '100'

        # Create call via ARI
        channel = ari_client.make_call(
            from_ext=from_ext,
            to_number=to_number,
            variables={'CRM_USER_ID': str(request.user.id)}
        )

        # Create call record
        call = Call.objects.create(
            asterisk_channel_id=channel.id,
            direction='outbound',
            from_number=from_ext,
            to_number=to_number,
            status='initiated',
            user=request.user,
            started_at=timezone.now(),
            contact_id=contact_id if contact_id else None,
            opportunity_id=opportunity_id if opportunity_id else None,
        )

        # Log the call initiation
        CallLog.objects.create(
            call=call,
            event='initiated',
            data={
                'from_ext': from_ext,
                'to_number': to_number,
                'channel_id': channel.id,
            }
        )

        return JsonResponse({
            'success': True,
            'call_id': call.id,
            'channel_id': channel.id,
        })

    except Exception as e:
        logger.error(f"Failed to initiate call: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def hangup_call(request, pk):
    """Hangup an active call"""
    call = get_object_or_404(Call, pk=pk)

    try:
        ari_client.hangup_call(call.asterisk_channel_id)

        # Update call status
        call.status = 'ended'
        call.ended_at = timezone.now()
        if call.answered_at:
            call.duration = int((call.ended_at - call.answered_at).total_seconds())
        call.save()

        CallLog.objects.create(
            call=call,
            event='hangup_requested',
            data={'user_id': request.user.id}
        )

        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Failed to hangup call {pk}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def answer_call(request, pk):
    """Answer a ringing call"""
    call = get_object_or_404(Call, pk=pk)

    if call.status != 'ringing':
        return JsonResponse({'error': 'Call is not ringing'}, status=400)

    try:
        ari_client.answer_call(call.asterisk_channel_id)

        # Update call status
        call.status = 'answered'
        call.answered_at = timezone.now()
        call.user = request.user
        call.save()

        CallLog.objects.create(
            call=call,
            event='answered',
            data={'user_id': request.user.id}
        )

        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Failed to answer call {pk}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def call_status(request, pk):
    """Get current call status (for polling) - checks Asterisk for live status"""
    call = get_object_or_404(Call, pk=pk)

    # If call is still active, check Asterisk for current status
    if call.status in ['initiated', 'ringing', 'answered']:
        try:
            channel = ari_client.get_channel(call.asterisk_channel_id)
            channel_state = channel.get('state', '')

            # Map Asterisk channel state to our status
            if channel_state == 'Up':
                if call.status != 'answered':
                    call.status = 'answered'
                    call.answered_at = timezone.now()
                    call.save()
                    CallLog.objects.create(
                        call=call,
                        event='answered',
                        data={'channel_state': channel_state}
                    )
            elif channel_state == 'Ringing':
                if call.status != 'ringing':
                    call.status = 'ringing'
                    call.save()
                    CallLog.objects.create(
                        call=call,
                        event='ringing',
                        data={'channel_state': channel_state}
                    )

            # Calculate live duration if answered
            if call.answered_at and call.status == 'answered':
                call.duration = int((timezone.now() - call.answered_at).total_seconds())

        except Exception as e:
            # Channel not found - call has ended
            logger.info(f"Channel {call.asterisk_channel_id} not found, marking call as ended: {e}")
            if call.status not in ['ended', 'failed', 'busy', 'no_answer']:
                call.status = 'ended'
                call.ended_at = timezone.now()
                if call.answered_at:
                    call.duration = int((call.ended_at - call.answered_at).total_seconds())
                call.save()
                CallLog.objects.create(
                    call=call,
                    event='ended',
                    data={'reason': 'channel_not_found'}
                )

    return JsonResponse({
        'status': call.status,
        'duration': call.duration,
        'started_at': call.started_at.isoformat() if call.started_at else None,
        'answered_at': call.answered_at.isoformat() if call.answered_at else None,
        'ended_at': call.ended_at.isoformat() if call.ended_at else None,
    })


@login_required
@require_POST
def update_call_notes(request, pk):
    """Update call notes"""
    call = get_object_or_404(Call, pk=pk)
    notes = request.POST.get('notes', '')

    call.notes = notes
    call.save(update_fields=['notes', 'updated_at'])

    return JsonResponse({'success': True})


@login_required
@require_POST
def link_call_to_contact(request, pk):
    """Link a call to a contact"""
    from apps.contacts.models import Contact

    call = get_object_or_404(Call, pk=pk)
    contact_id = request.POST.get('contact_id')

    if contact_id:
        contact = get_object_or_404(Contact, pk=contact_id)
        call.contact = contact
        call.save(update_fields=['contact', 'updated_at'])

    return JsonResponse({'success': True})


@login_required
@require_POST
def link_call_to_opportunity(request, pk):
    """Link a call to an opportunity"""
    from apps.crm.models import Lead

    call = get_object_or_404(Call, pk=pk)
    opportunity_id = request.POST.get('opportunity_id')

    if opportunity_id:
        opportunity = get_object_or_404(Lead, pk=opportunity_id)
        call.opportunity = opportunity
        call.save(update_fields=['opportunity', 'updated_at'])

    return JsonResponse({'success': True})


@login_required
def recording_download(request, pk):
    """Download call recording"""
    recording = get_object_or_404(CallRecording, pk=pk)

    response = HttpResponse(recording.file, content_type='audio/mpeg')
    response['Content-Disposition'] = f'attachment; filename="{recording.call.asterisk_uniqueid}.mp3"'
    return response


@login_required
def active_calls(request):
    """Get list of active calls (for dashboard widget)"""
    active = Call.objects.filter(
        status__in=['initiated', 'ringing', 'answered']
    ).select_related('user', 'contact')

    calls_data = [{
        'id': call.id,
        'direction': call.direction,
        'status': call.status,
        'from_number': call.from_number,
        'to_number': call.to_number,
        'user': call.user.username if call.user else None,
        'contact_name': call.contact.name if call.contact else None,
        'started_at': call.started_at.isoformat() if call.started_at else None,
    } for call in active]

    return JsonResponse({'calls': calls_data})


class SIPSettingsForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
    )

    class Meta:
        model = SIPSettings
        fields = ['server_ip', 'server_port', 'username', 'caller_id', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not (self.instance and self.instance.pk):
            self.fields['password'].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            instance.password = password  # uses the encrypting setter
        if commit:
            instance.save()
        return instance


@login_required
def sip_settings_view(request):
    """SIP credentials settings page"""
    from .asterisk_config import apply_sip_settings

    try:
        sip = request.user.sip_settings
    except SIPSettings.DoesNotExist:
        sip = None

    if request.method == 'POST':
        if 'delete' in request.POST:
            if sip:
                sip.delete()
                apply_sip_settings(None)
                messages.success(request, 'SIP credentials deleted. Asterisk config cleared.')
            return redirect('settings_voip')

        form = SIPSettingsForm(request.POST, instance=sip)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            if apply_sip_settings(obj):
                messages.success(request, 'SIP credentials saved and Asterisk reloaded.')
            else:
                messages.warning(request, 'SIP credentials saved but Asterisk reload failed. You may need to restart the Asterisk container.')
            return redirect('settings_voip')
    else:
        form = SIPSettingsForm(instance=sip)

    return render(request, 'calls/sip_settings.html', {
        'form': form,
        'sip_settings': sip,
    })
