"""
Template views — existing Django views preserved during DRF transition.

These views render HTML templates and use ActivityService for business logic.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.crm.models import SalesTeam
from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..forms import ActivityForm
from ..models import Activity
from ..services import ActivityService


@login_required
def activity_dashboard(request):
    """Activities dashboard — renders Svelte shell."""
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    from apps.activities.models import ActivityType

    available_teams = SalesTeam.objects.filter(is_active=True) if request.user.is_sales_executive() else []
    user_team_id = request.user.sales_team.id if request.user.sales_team else None
    activity_types_data = list(
        ActivityType.objects.filter(is_active=True).values("id", "name", "icon", "color")
    )

    init_data = {
        "isManager": request.user.is_sales_manager(),
        "isExecutive": request.user.is_sales_executive(),
        "userTeamId": user_team_id,
        "availableTeams": [{"id": t.id, "name": t.name} for t in available_teams],
        "activityTypes": activity_types_data,
        "apiUrls": {
            "activities": "/activities/api/activities/",
            "activityTypes": "/activities/api/activity-types/",
        },
    }

    return render(request, "activities/dashboard.html", {
        "init_data_json": json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def activity_create(request):
    """Create new activity — must be called with lead_id parameter"""
    lead_id = request.GET.get("lead_id")

    if not lead_id:
        messages.error(request, "Activities must be created from an opportunity detail page.")
        return redirect("activities:dashboard")

    if request.method == "POST":
        form = ActivityForm(request.POST, user=request.user, lead_id=lead_id)
        if form.is_valid():
            form.save()
            return redirect("activities:dashboard")
    else:
        form = ActivityForm(user=request.user, lead_id=lead_id)

    return render(request, "activities/activity_form.html", {"form": form, "action": "Create Activity"})


@login_required
def activity_detail(request, pk):
    """View activity detail"""
    activity = get_object_or_404(
        Activity.objects.select_related("activity_type", "lead", "assigned_to", "created_by"),
        pk=pk,
    )

    if not activity.can_be_viewed_by(request.user):
        raise Http404()

    # For Phone Call activities, pass the PhoneCallExtension for call details display
    phone_call = getattr(activity, "phone_call", None)

    return render(
        request,
        "activities/activity_detail.html",
        {"activity": activity, "phone_call": phone_call, "can_edit": activity.can_be_edited_by(request.user)},
    )


@login_required
def activity_edit(request, pk):
    """Edit existing activity"""
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_be_edited_by(request.user):
        raise Http404()

    if request.method == "POST":
        form = ActivityForm(request.POST, instance=activity, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("activities:dashboard")
    else:
        form = ActivityForm(instance=activity, user=request.user)

    phone_call = getattr(activity, "phone_call", None)
    return render(
        request,
        "activities/activity_form.html",
        {"form": form, "activity": activity, "action": "Edit Activity", "phone_call": phone_call},
    )


@login_required
def activity_delete(request, pk):
    """Delete activity"""
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_be_edited_by(request.user):
        raise Http404()

    if request.method == "POST":
        activity.delete()
        return redirect("activities:dashboard")

    return render(request, "activities/activity_confirm_delete.html", {"activity": activity})


@login_required
def activity_complete(request, pk):
    """Mark activity as complete with outcome"""
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_be_edited_by(request.user):
        raise Http404()

    if request.method == "POST":
        outcome = request.POST.get("outcome", "")
        try:
            ActivityService.complete_activity(pk=pk, user=request.user, outcome=outcome)
        except (PermissionDeniedError, ValidationError) as e:
            messages.error(request, str(e.message))
            return redirect("activities:dashboard")
        return redirect("activities:dashboard")

    return render(request, "activities/activity_complete.html", {"activity": activity})


# ── Call-action endpoints (PhoneCallExtension is the primary business record) ─

def _get_phone_call_ext(activity_pk):
    """Return (activity, phone_call_extension | None)."""
    activity = get_object_or_404(
        Activity.objects.select_related("phone_call"),
        pk=activity_pk,
    )
    ext = getattr(activity, "phone_call", None)
    return activity, ext


@login_required
@require_GET
def activity_call_status(request, pk):
    """Poll call status via the PhoneCallExtension / Asterisk channel."""
    from apps.calls.services import CallService

    activity, ext = _get_phone_call_ext(pk)
    if not ext or not ext.ari_call_id:
        # Fall back to extension data if no ARI call (e.g. channel already gone)
        if ext:
            return JsonResponse({
                "status": ext.call_status,
                "duration": ext.duration,
                "started_at": ext.started_at.isoformat() if ext.started_at else None,
                "answered_at": ext.answered_at.isoformat() if ext.answered_at else None,
                "ended_at": ext.ended_at.isoformat() if ext.ended_at else None,
            })
        return JsonResponse({"error": "No call linked to this activity"}, status=404)
    try:
        status_data = CallService.get_call_status(call_pk=ext.ari_call_id)
        return JsonResponse(status_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)


@login_required
@require_POST
def activity_call_hangup(request, pk):
    """Hang up the call linked to this activity."""
    from apps.calls.services import CallService

    activity, ext = _get_phone_call_ext(pk)
    if not ext or not ext.ari_call_id:
        return JsonResponse({"error": "No active call linked to this activity"}, status=404)
    try:
        CallService.hangup_call(call_pk=ext.ari_call_id, user=request.user)
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def activity_call_ended(request, pk):
    """Mark the linked call as ended (called by browser WebRTC session end event)."""
    from django.utils import timezone

    activity, ext = _get_phone_call_ext(pk)
    if not ext:
        return JsonResponse({"success": True})  # already gone, no-op

    if ext.call_status in ("ended", "failed"):
        return JsonResponse({"success": True})

    now = timezone.now()
    ext.call_status = "ended"
    ext.ended_at = now
    if ext.answered_at:
        ext.duration = int((now - ext.answered_at).total_seconds())
    ext.save(update_fields=["call_status", "ended_at", "duration", "updated_at"])

    # Also mark the underlying ARI call record
    if ext.ari_call_id:
        ari = ext.ari_call
        if ari.status not in ("ended", "failed"):
            ari.status = "ended"
            ari.ended_at = now
            ari.duration = ext.duration
            ari.save(update_fields=["status", "ended_at", "duration", "updated_at"])
        # Recording is triggered by the ARI ChannelDestroyed event.
        # Do NOT queue it here — the browser SIP end-event races with ARI
        # and causes duplicate processing.

    return JsonResponse({"success": True})


@login_required
@require_POST
def activity_call_notes(request, pk):
    """Save in-call notes into the activity's description."""
    activity, _ = _get_phone_call_ext(pk)
    notes = request.POST.get("notes", "")
    activity.description = notes
    activity.save(update_fields=["description", "updated_at"])
    return JsonResponse({"success": True})


@login_required
@require_POST
def activity_call_link_contact(request, pk):
    """Link a contact to this activity's PhoneCallExtension (and ARI call)."""
    from apps.calls.services import CallService

    activity, ext = _get_phone_call_ext(pk)
    contact_id = request.POST.get("contact_id")
    if not contact_id:
        return JsonResponse({"error": "contact_id is required"}, status=400)
    try:
        if ext and ext.ari_call_id:
            # CallService.link_call_to_contact also updates ext.contact via the sync logic
            CallService.link_call_to_contact(call_pk=ext.ari_call_id, contact_id=int(contact_id))
        elif ext:
            from apps.contacts.models import Contact
            contact = get_object_or_404(Contact, pk=int(contact_id))
            ext.contact = contact
            ext.save(update_fields=["contact", "updated_at"])
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)


@login_required
@require_POST
def activity_call_link_opportunity(request, pk):
    """Link an opportunity to this activity (and its ARI call)."""
    from apps.calls.services import CallService
    from apps.crm.models import Lead

    activity, ext = _get_phone_call_ext(pk)
    opportunity_id = request.POST.get("opportunity_id")
    if not opportunity_id:
        return JsonResponse({"error": "opportunity_id is required"}, status=400)
    try:
        lead = Lead.objects.get(pk=int(opportunity_id))
        activity.lead = lead
        activity.save(update_fields=["lead", "updated_at"])
        if ext and ext.ari_call_id:
            CallService.link_call_to_opportunity(call_pk=ext.ari_call_id, lead_id=int(opportunity_id))
        return JsonResponse({"success": True})
    except Lead.DoesNotExist:
        return JsonResponse({"error": "Opportunity not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
