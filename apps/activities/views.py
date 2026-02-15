from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.utils import timezone
from datetime import date, timedelta
from .models import Activity, ActivityType
from .forms import ActivityForm
from apps.crm.models import SalesTeam


@login_required
def activity_dashboard(request):
    """Dashboard view with date filtering and team selection"""
    view_context = request.GET.get('view', 'personal')
    selected_team_id = request.GET.get('team', 'all')
    date_filter = request.GET.get('filter', 'week')
    custom_date = request.GET.get('date', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Permission check for team view
    if view_context == 'team' and not (request.user.is_sales_manager() or request.user.is_sales_executive()):
        view_context = 'personal'

    # Get base queryset based on view context
    if view_context == 'team':
        if request.user.is_sales_executive():
            if selected_team_id == 'all':
                activities = Activity.objects.all()
            else:
                try:
                    target_team = SalesTeam.objects.get(id=selected_team_id)
                    team_members = target_team.get_team_members()
                    activities = Activity.objects.filter(lead__assigned_to__in=team_members)
                except SalesTeam.DoesNotExist:
                    activities = Activity.objects.none()
        else:
            # Manager sees only their team
            if request.user.sales_team:
                team_members = request.user.sales_team.get_team_members()
                activities = Activity.objects.filter(lead__assigned_to__in=team_members)
            else:
                activities = Activity.objects.none()
    else:
        # Personal view - only user's activities
        activities = Activity.objects.filter(lead__assigned_to=request.user)

    # Apply date filtering
    today = date.today()

    if date_filter == 'today':
        activities = activities.filter(scheduled_date=today)
    elif date_filter == 'week':
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        activities = activities.filter(scheduled_date__range=[start_week, end_week])
    elif date_filter == 'next_week':
        start_week = today - timedelta(days=today.weekday())
        start_next = start_week + timedelta(days=7)
        end_next = start_next + timedelta(days=6)
        activities = activities.filter(scheduled_date__range=[start_next, end_next])
    elif date_filter == 'future':
        activities = activities.filter(scheduled_date__gt=today)
    elif date_filter == 'past':
        activities = activities.filter(scheduled_date__lt=today)
    elif date_filter == 'custom' and custom_date:
        activities = activities.filter(scheduled_date=custom_date)
    elif date_filter == 'range' and start_date and end_date:
        activities = activities.filter(scheduled_date__range=[start_date, end_date])

    # Order by scheduled date
    activities = activities.select_related('lead', 'activity_type', 'assigned_to').order_by('scheduled_date', 'created_at')

    # Get available teams for executives
    available_teams = []
    if request.user.is_sales_executive():
        available_teams = SalesTeam.objects.filter(is_active=True)

    # Get user's team ID for managers
    user_team_id = request.user.sales_team.id if request.user.sales_team else None

    context = {
        'activities': activities,
        'view_context': view_context,
        'selected_team_id': selected_team_id,
        'date_filter': date_filter,
        'custom_date': custom_date,
        'start_date': start_date,
        'end_date': end_date,
        'available_teams': available_teams,
        'user_team_id': user_team_id,
        'today': today,
    }

    return render(request, 'activities/dashboard.html', context)


@login_required
def activity_create(request):
    """Create new activity - must be called with lead_id parameter"""
    lead_id = request.GET.get('lead_id')

    # Require lead_id parameter
    if not lead_id:
        messages.error(request, 'Activities must be created from an opportunity detail page.')
        return redirect('activities:dashboard')

    if request.method == 'POST':
        form = ActivityForm(request.POST, user=request.user, lead_id=lead_id)
        if form.is_valid():
            activity = form.save()
            return redirect('activities:dashboard')
    else:
        form = ActivityForm(user=request.user, lead_id=lead_id)

    return render(request, 'activities/activity_form.html', {
        'form': form,
        'action': 'Create Activity'
    })


@login_required
def activity_detail(request, pk):
    """View activity detail"""
    activity = get_object_or_404(Activity, pk=pk)

    # Permission check
    if not activity.can_be_viewed_by(request.user):
        raise Http404()

    return render(request, 'activities/activity_detail.html', {'activity': activity})


@login_required
def activity_edit(request, pk):
    """Edit existing activity"""
    activity = get_object_or_404(Activity, pk=pk)

    # Permission check
    if not activity.can_be_edited_by(request.user):
        raise Http404()

    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('activities:dashboard')
    else:
        form = ActivityForm(instance=activity, user=request.user)

    return render(request, 'activities/activity_form.html', {
        'form': form,
        'activity': activity,
        'action': 'Edit Activity'
    })


@login_required
def activity_delete(request, pk):
    """Delete activity"""
    activity = get_object_or_404(Activity, pk=pk)

    # Permission check
    if not activity.can_be_edited_by(request.user):
        raise Http404()

    if request.method == 'POST':
        activity.delete()
        return redirect('activities:dashboard')

    return render(request, 'activities/activity_confirm_delete.html', {'activity': activity})


@login_required
def activity_complete(request, pk):
    """Mark activity as complete with outcome"""
    activity = get_object_or_404(Activity, pk=pk)

    # Permission check
    if not activity.can_be_edited_by(request.user):
        raise Http404()

    if request.method == 'POST':
        outcome = request.POST.get('outcome', '')
        activity.status = 'completed'
        activity.outcome = outcome
        activity.completed_at = timezone.now()
        activity.save()
        return redirect('activities:dashboard')

    return render(request, 'activities/activity_complete.html', {'activity': activity})
