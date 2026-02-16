"""
Template views -- existing Django views preserved during DRF transition.

These views render HTML templates. Business logic that was previously inline
has been moved to CallService where appropriate.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from ..models import Call, CallRecording, SIPSettings
from ..services import CallService
from ..tasks import process_recording


@login_required
def call_list(request):
    """Display list of all calls"""
    direction = request.GET.get("direction")
    status = request.GET.get("status")
    user_filter = request.GET.get("user")
    search = request.GET.get("search", "").strip()

    calls = CallService.list_calls_for_user(
        user=request.user,
        direction=direction,
        status=status,
        user_filter=user_filter,
        search=search,
    )

    # Pagination
    paginator = Paginator(calls, 25)
    page = request.GET.get("page", 1)
    calls = paginator.get_page(page)

    context = {
        "calls": calls,
        "direction_filter": direction,
        "status_filter": status,
        "user_filter": user_filter,
        "search": search,
    }
    return render(request, "calls/call_list.html", context)


@login_required
def call_detail(request, pk):
    """Display call details"""
    call = get_object_or_404(
        Call.objects.select_related("contact", "opportunity", "user", "recording"),
        pk=pk,
    )
    logs = call.logs.order_by("timestamp")

    context = {
        "call": call,
        "logs": logs,
    }
    return render(request, "calls/call_detail.html", context)


@login_required
def dialpad(request):
    """Display dialpad for making calls"""
    from apps.contacts.models import Contact

    recent_contacts = Contact.objects.all()[:10]

    # Agent's WebRTC extension (default 100)
    agent_extension = getattr(request.user, "extension", None) or "100"

    context = {
        "recent_contacts": recent_contacts,
        "ws_url": "ws://localhost:8088/ws",
        "sip_extension": agent_extension,
        "sip_domain": "localhost",
    }
    return render(request, "calls/dialpad.html", context)


@login_required
@require_POST
def register_inbound_call(request):
    """Register an inbound call when the agent answers it in the browser."""
    from_number = request.POST.get("from_number", "").strip()

    call = Call.objects.create(
        direction="inbound",
        from_number=from_number,
        to_number=getattr(request.user, "extension", None) or "100",
        status="answered",
        user=request.user,
        started_at=timezone.now(),
        answered_at=timezone.now(),
    )
    return JsonResponse({"success": True, "call_id": call.id})


@login_required
@require_POST
def call_ended(request, pk):
    """Mark an inbound call as ended and trigger recording processing."""
    try:
        call = Call.objects.get(pk=pk, user=request.user)
    except Call.DoesNotExist:
        return JsonResponse({"error": "Call not found"}, status=404)

    if call.status in ("ended", "failed"):
        return JsonResponse({"success": True, "call_id": call.id})

    call.status = "ended"
    call.ended_at = timezone.now()
    if call.answered_at:
        call.duration = int((call.ended_at - call.answered_at).total_seconds())
    call.save()

    process_recording.delay(call.id)

    return JsonResponse({"success": True, "call_id": call.id})


@login_required
@require_POST
def initiate_call(request):
    """Initiate an outbound call via AJAX"""
    to_number = request.POST.get("to_number", "").strip()
    contact_id = request.POST.get("contact_id")
    opportunity_id = request.POST.get("opportunity_id")

    try:
        call = CallService.initiate_call(
            user=request.user,
            phone_number=to_number,
            contact_id=int(contact_id) if contact_id else None,
            lead_id=int(opportunity_id) if opportunity_id else None,
        )
        return JsonResponse({
            "success": True,
            "call_id": call.id,
            "channel_id": call.asterisk_channel_id,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400 if "required" in str(e) else 500)


@login_required
@require_POST
def hangup_call(request, pk):
    """Hangup an active call"""
    try:
        CallService.hangup_call(call_pk=pk, user=request.user)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def answer_call(request, pk):
    """Answer a ringing call"""
    try:
        CallService.answer_call(call_pk=pk, user=request.user)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400 if "not ringing" in str(e) else 500)


@login_required
@require_GET
def call_status(request, pk):
    """Get current call status (for polling)"""
    try:
        status_data = CallService.get_call_status(call_pk=pk)
        return JsonResponse(status_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)


@login_required
@require_POST
def update_call_notes(request, pk):
    """Update call notes"""
    notes = request.POST.get("notes", "")

    try:
        CallService.update_call_notes(call_pk=pk, user=request.user, notes=notes)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)


@login_required
@require_POST
def link_call_to_contact(request, pk):
    """Link a call to a contact"""
    contact_id = request.POST.get("contact_id")

    if contact_id:
        try:
            CallService.link_call_to_contact(call_pk=pk, contact_id=int(contact_id))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=404)

    return JsonResponse({"success": True})


@login_required
@require_POST
def link_call_to_opportunity(request, pk):
    """Link a call to an opportunity"""
    opportunity_id = request.POST.get("opportunity_id")

    if opportunity_id:
        try:
            CallService.link_call_to_opportunity(call_pk=pk, lead_id=int(opportunity_id))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=404)

    return JsonResponse({"success": True})


@login_required
def recording_download(request, pk):
    """Download call recording"""
    recording = get_object_or_404(CallRecording, pk=pk)

    response = HttpResponse(recording.file, content_type="audio/mpeg")
    response["Content-Disposition"] = (
        f'attachment; filename="{recording.call.asterisk_uniqueid}.mp3"'
    )
    return response


@login_required
def active_calls(request):
    """Get list of active calls (for dashboard widget)"""
    calls_data = CallService.get_active_calls(user=request.user)
    return JsonResponse({"calls": calls_data})


class SIPSettingsForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=True, attrs={"autocomplete": "new-password"}),
        required=False,
    )

    class Meta:
        model = SIPSettings
        fields = ["server_ip", "server_port", "username", "caller_id", "is_active", "hold_music"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["password"].initial = self.instance.password
        else:
            self.fields["password"].required = True

    def clean(self):
        cleaned = super().clean()

        # Validate hold_music file extension
        hold_music = cleaned.get("hold_music")
        if hold_music and hasattr(hold_music, "name"):
            ext = hold_music.name.rsplit(".", 1)[-1].lower() if "." in hold_music.name else ""
            if ext not in ("mp3", "wav"):
                self.add_error("hold_music", "Only mp3 and wav files are supported.")

        server_ip = cleaned.get("server_ip")
        server_port = cleaned.get("server_port")
        username = cleaned.get("username")
        password = cleaned.get("password")

        # For existing settings with no new password, use stored password
        if not password and self.instance and self.instance.pk:
            password = self.instance.password

        if not all([server_ip, server_port, username, password]):
            return cleaned

        # Only validate if the trunk will be active
        if not cleaned.get("is_active", True):
            return cleaned

        from ..sip_validator import validate_sip_credentials

        is_valid, error = validate_sip_credentials(
            server_ip, server_port, username, password
        )
        if not is_valid:
            raise forms.ValidationError(f"SIP credential test failed: {error}")

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            instance.password = password  # uses the encrypting setter
        if commit:
            instance.save()
        return instance


@login_required
def sip_settings_view(request):
    """SIP credentials settings page"""
    from ..asterisk_config import apply_moh_settings, apply_sip_settings

    try:
        sip = request.user.sip_settings
    except SIPSettings.DoesNotExist:
        sip = None

    if request.method == "POST":
        if "delete" in request.POST:
            if sip:
                sip.delete()
                apply_sip_settings(None)
                messages.success(request, "SIP credentials deleted. Asterisk config cleared.")
            return redirect("settings_voip")

        # Handle hold music removal
        if "remove_hold_music" in request.POST and sip and sip.hold_music:
            sip.hold_music.delete(save=False)
            sip.hold_music = None
            sip.save()
            apply_moh_settings(sip)
            messages.success(request, "Hold music removed. Default music will be used.")
            return redirect("settings_voip")

        form = SIPSettingsForm(request.POST, request.FILES, instance=sip)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()

            # Apply MOH settings if hold music was uploaded
            if "hold_music" in request.FILES:
                apply_moh_settings(obj)

            if apply_sip_settings(obj):
                messages.success(request, "SIP credentials saved and Asterisk reloaded.")
            else:
                messages.warning(
                    request,
                    "SIP credentials saved but Asterisk reload failed. "
                    "You may need to restart the Asterisk container.",
                )
            return redirect("settings_voip")
    else:
        form = SIPSettingsForm(instance=sip)

    return render(request, "calls/sip_settings.html", {
        "form": form,
        "sip_settings": sip,
    })
