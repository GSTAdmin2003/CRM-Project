"""
Template views — existing Django views preserved during DRF transition.

These views render HTML templates and use ActivityService for business logic.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.crm.models import SalesTeam
from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..forms import ActivityForm
from ..models import Activity
from ..services import ActivityService


@login_required
def activity_dashboard(request):
    """Dashboard view with date filtering and team selection"""
    view_context = request.GET.get("view", "personal")
    selected_team_id = request.GET.get("team", "all")
    date_filter = request.GET.get("filter", "week")
    custom_date = request.GET.get("date", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    # Permission check for team view
    if view_context == "team" and not (
        request.user.is_sales_manager() or request.user.is_sales_executive()
    ):
        view_context = "personal"

    activities = ActivityService.get_activities_for_user(
        user=request.user,
        view_context=view_context,
        team_id=selected_team_id,
        date_filter=date_filter,
        custom_date=custom_date,
        start_date=start_date,
        end_date=end_date,
    )

    # Get available teams for executives
    available_teams = []
    if request.user.is_sales_executive():
        available_teams = SalesTeam.objects.filter(is_active=True)

    user_team_id = request.user.sales_team.id if request.user.sales_team else None

    context = {
        "activities": activities,
        "view_context": view_context,
        "selected_team_id": selected_team_id,
        "date_filter": date_filter,
        "custom_date": custom_date,
        "start_date": start_date,
        "end_date": end_date,
        "available_teams": available_teams,
        "user_team_id": user_team_id,
        "today": __import__("datetime").date.today(),
    }

    return render(request, "activities/dashboard.html", context)


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
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_be_viewed_by(request.user):
        raise Http404()

    return render(request, "activities/activity_detail.html", {"activity": activity})


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

    return render(
        request,
        "activities/activity_form.html",
        {"form": form, "activity": activity, "action": "Edit Activity"},
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
