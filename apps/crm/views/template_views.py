"""
Template views -- existing Django views preserved during DRF transition.

These views render HTML templates. The old API-style function views
(api_kanban_data, api_update_lead_stage, etc.) are kept here for backward
compatibility with existing template JS code.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.activities.models import Activity
from apps.contacts.models import Company, Contact
from core.models import User

from ..forms import IncomingLeadForm
from ..models import IncomingLead, Lead, LeadActivity, LeadStage, SalesTeam

from datetime import timedelta


@login_required
def crm_dashboard(request):
    """CRM main dashboard"""
    user_leads = request.user.get_accessible_leads_queryset()

    # Get this week's activities based on user role
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    week_activities = request.user.get_accessible_activities_queryset().filter(
        scheduled_date__gte=week_start,
        scheduled_date__lte=week_end
    ).select_related('activity_type', 'lead', 'assigned_to').order_by('scheduled_date', 'created_at')

    context = {
        'total_leads': user_leads.count(),
        'total_value': user_leads.aggregate(total=Sum('estimated_value'))['total'] or 0,
        'week_activities': week_activities,
    }

    return render(request, 'crm/dashboard.html', context)


@login_required
def kanban_board(request):
    """Kanban board view"""
    # Get view context (personal or team)
    view_context = request.GET.get('view', 'personal')
    selected_team_id = request.GET.get('team', 'all')

    # Validate view context based on user permissions
    if view_context == 'team' and not (request.user.is_sales_manager() or request.user.is_sales_executive()):
        view_context = 'personal'

    # Determine which team to show based on permissions and selection
    target_team = None
    if view_context == 'team':
        if request.user.is_sales_executive():
            # Executives can view any team or all teams
            if selected_team_id != 'all':
                try:
                    target_team = SalesTeam.objects.get(id=selected_team_id)
                except SalesTeam.DoesNotExist:
                    selected_team_id = 'all'
        else:
            # Managers can only view their own team
            target_team = request.user.sales_team
            selected_team_id = str(target_team.id) if target_team else 'all'
    else:
        # For personal view, use user's team for stage selection
        target_team = request.user.sales_team

    # Get stages for the current context
    if view_context == 'team' and selected_team_id == 'all':
        # Show global stages when viewing all teams
        stages = LeadStage.objects.filter(sales_team=None, is_active=True).order_by('order')
    else:
        # Use team-specific stages or fallback to global
        stages = LeadStage.get_stages_for_team(target_team)

    # Get available teams for team selector (executives only)
    available_teams = []
    if request.user.is_sales_executive():
        available_teams = SalesTeam.objects.filter(is_active=True).order_by('name')

    context = {
        'view_context': view_context,
        'stages': stages,
        'available_teams': available_teams,
        'selected_team_id': selected_team_id,
        'user_team_id': request.user.sales_team.id if request.user.sales_team else None,
    }

    return render(request, 'crm/kanban.html', context)


@login_required
@require_http_methods(["GET"])
def api_kanban_data(request):
    """API endpoint for kanban data"""
    view_context = request.GET.get('view', 'personal')
    selected_team_id = request.GET.get('team', 'all')

    # Determine target team based on permissions and selection
    target_team = None
    if view_context == 'team':
        if request.user.is_sales_executive():
            # Executives can view any team or all teams
            if selected_team_id != 'all':
                try:
                    target_team = SalesTeam.objects.get(id=selected_team_id)
                except SalesTeam.DoesNotExist:
                    selected_team_id = 'all'
        else:
            # Managers can only view their own team
            target_team = request.user.sales_team
    else:
        # For personal view, use user's team for stage selection
        target_team = request.user.sales_team

    # Get leads based on view context and team selection
    if view_context == 'team':
        if selected_team_id == 'all' and request.user.is_sales_executive():
            # Show all leads across all teams
            leads = Lead.objects.all()
        elif target_team:
            # Show leads for specific team
            team_members = target_team.get_team_members()
            leads = Lead.objects.filter(assigned_to__in=team_members)
        else:
            # Fallback to user's own leads
            leads = Lead.objects.filter(assigned_to=request.user)
    else:
        # Personal view - user's own leads
        leads = Lead.objects.filter(assigned_to=request.user)

    # Get stages based on view context and team selection
    if view_context == 'team' and selected_team_id == 'all':
        # Show global stages when viewing all teams
        stages = LeadStage.objects.filter(sales_team=None, is_active=True).order_by('order')
    else:
        # Use team-specific stages or fallback to global
        stages = LeadStage.get_stages_for_team(target_team)

    kanban_data = []

    for stage in stages:
        stage_leads = leads.filter(stage=stage)
        lead_data = []

        for lead in stage_leads:
            lead_data.append({
                'id': lead.id,
                'title': lead.title,
                'full_name': lead.full_name,
                'company_name': lead.company_name,
                'estimated_value': str(lead.estimated_value),
                'probability': lead.probability,
                'assigned_to': lead.assigned_to.get_full_name() if lead.assigned_to else '',
                'created_at': lead.created_at.isoformat(),
                'last_activity': lead.last_activity.isoformat(),
            })

        kanban_data.append({
            'stage': {
                'id': stage.id,
                'name': stage.name,
                'color': stage.color,
                'probability': stage.probability,
            },
            'leads': lead_data,
            'total_value': sum(float(lead.estimated_value) for lead in stage_leads),
            'count': len(lead_data),
        })

    return JsonResponse({'stages': kanban_data})


@login_required
@csrf_exempt
@require_http_methods(["PATCH"])
def api_update_lead_stage(request, lead_id):
    """API endpoint to update lead stage (for drag & drop)"""
    try:
        lead = get_object_or_404(Lead, id=lead_id)

        # Check permissions
        if not lead.can_be_edited_by(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        data = json.loads(request.body)
        new_stage_id = data.get('stage_id')

        if not new_stage_id:
            return JsonResponse({'error': 'Stage ID is required'}, status=400)

        new_stage = get_object_or_404(LeadStage, id=new_stage_id)
        old_stage = lead.stage

        # Update lead stage
        lead.stage = new_stage
        lead.probability = new_stage.probability  # Update probability to stage default
        lead.save()

        # Log activity
        LeadActivity.objects.create(
            lead=lead,
            user=request.user,
            activity_type='stage_change',
            subject=f'Stage changed from {old_stage.name} to {new_stage.name}',
            description=f'Opportunity moved from {old_stage.name} to {new_stage.name}'
        )

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_lead_list_create(request):
    """API endpoint for lead list and creation"""
    if request.method == 'GET':
        leads = request.user.get_accessible_leads_queryset()
        lead_data = []

        for lead in leads:
            lead_data.append({
                'id': lead.id,
                'title': lead.title,
                'full_name': lead.full_name,
                'email': lead.email,
                'company_name': lead.company_name,
                'stage': lead.stage.name,
                'estimated_value': str(lead.estimated_value),
                'assigned_to': lead.assigned_to.get_full_name() if lead.assigned_to else '',
            })

        return JsonResponse({'leads': lead_data})

    elif request.method == 'POST':
        # Handle lead creation
        pass  # Will implement in next phase

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_lead_detail(request, lead_id):
    """API endpoint for lead detail"""
    lead = get_object_or_404(Lead, id=lead_id)

    if not lead.can_be_viewed_by(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    lead_data = {
        'id': lead.id,
        'title': lead.title,
        'first_name': lead.first_name,
        'last_name': lead.last_name,
        'email': lead.email,
        'phone': lead.phone,
        'company_name': lead.company_name,
        'position': lead.position,
        'stage': {
            'id': lead.stage.id,
            'name': lead.stage.name,
        },
        'estimated_value': str(lead.estimated_value),
        'probability': lead.probability,
        'expected_close_date': lead.expected_close_date.isoformat() if lead.expected_close_date else None,
        'source': lead.source,
        'status': lead.status,
        'notes': lead.notes,
        'assigned_to': lead.assigned_to.get_full_name() if lead.assigned_to else '',
        'created_at': lead.created_at.isoformat(),
        'updated_at': lead.updated_at.isoformat(),
        'activities': [
            {
                'type': activity.activity_type,
                'subject': activity.subject,
                'description': activity.description,
                'user': activity.user.get_full_name() if activity.user else '',
                'created_at': activity.created_at.isoformat(),
            }
            for activity in lead.activities.all()[:20]
        ]
    }

    return JsonResponse({'lead': lead_data})


@login_required
@require_http_methods(["POST"])
def api_quick_activity_create(request):
    """API endpoint for quick activity creation from opportunity form"""
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        activity_type_id = data.get('activity_type_id')
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        scheduled_date = data.get('scheduled_date')

        if not all([lead_id, activity_type_id, title, scheduled_date]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        lead = get_object_or_404(Lead, pk=lead_id)
        if not lead.can_be_edited_by(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        from apps.activities.models import ActivityType
        activity_type = get_object_or_404(ActivityType, pk=activity_type_id)

        activity = Activity.objects.create(
            lead=lead,
            activity_type=activity_type,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            assigned_to=request.user,
            created_by=request.user,
            status='planned',
        )

        return JsonResponse({
            'success': True,
            'activity': {
                'id': activity.id,
                'title': activity.title,
                'activity_type': activity.activity_type.name,
                'scheduled_date': str(activity.scheduled_date),
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Regular views (for non-API usage)
@login_required
def lead_list(request):
    """Lead list view"""
    leads = request.user.get_accessible_leads_queryset()
    return render(request, 'crm/lead_list.html', {'leads': leads})


@login_required
def lead_create(request):
    """Lead creation view"""
    from ..forms import LeadForm

    if request.method == 'POST':
        form = LeadForm(request.POST, user=request.user)
        if form.is_valid():
            lead = form.save()

            # Create initial activity
            LeadActivity.objects.create(
                lead=lead,
                user=request.user,
                activity_type='created',
                subject=f'Opportunity "{lead.title}" created',
                description=f'New opportunity created for {lead.company.legal_name if lead.company else "unknown company"}'
            )

            return redirect('crm:kanban_board')
    else:
        form = LeadForm(user=request.user)

    # Get stages for the status bar based on user's team
    user_team = request.user.sales_team
    stages = LeadStage.get_stages_for_team(user_team)

    # Get all contacts for the contact selector, grouped by company
    contacts_by_company = {}

    # Group contacts by company and prioritize favorite contacts
    companies_with_contacts = Company.objects.filter(contacts__isnull=False).distinct()

    for company in companies_with_contacts:
        company_contacts = company.contacts.all()
        contact_list = []

        # Add favorite contact first if it exists
        if company.favorite_contact and company.favorite_contact in company_contacts:
            contact_list.append({
                'id': company.favorite_contact.id,
                'name': company.favorite_contact.name,
                'email': company.favorite_contact.email,
                'phone': company.favorite_contact.phone,
                'mobile': company.favorite_contact.mobile,
                'position': company.favorite_contact.position,
                'is_favorite': True,
            })
            # Add other contacts (excluding favorite)
            for contact in company_contacts.exclude(id=company.favorite_contact.id):
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })
        else:
            # No favorite contact, add all contacts
            for contact in company_contacts:
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })

        contacts_by_company[company.id] = contact_list

    return render(request, 'crm/lead_form.html', {
        'form': form,
        'stages': stages,
        'contacts_by_company_json': json.dumps(contacts_by_company),
        'selected_contact_id': form.selected_contact_id if hasattr(form, 'selected_contact_id') else '',
    })


@login_required
def lead_edit(request, pk):
    """Lead edit view"""
    from ..forms import LeadForm

    lead = get_object_or_404(Lead, pk=pk)
    if not lead.can_be_edited_by(request.user):
        raise Http404()

    # Get filter context from query params for navigation
    view_context = request.GET.get('view', 'personal')
    selected_team_id = request.GET.get('team', 'all')
    selected_stage_id = request.GET.get('stage', '')

    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead, user=request.user)
        if form.is_valid():
            old_stage = lead.stage
            lead = form.save()

            # Log stage change if it occurred
            if old_stage != lead.stage:
                LeadActivity.objects.create(
                    lead=lead,
                    user=request.user,
                    activity_type='stage_change',
                    subject=f'Stage changed from {old_stage.name} to {lead.stage.name}',
                    description=f'Opportunity stage updated from {old_stage.name} to {lead.stage.name}'
                )

            # Log general update
            LeadActivity.objects.create(
                lead=lead,
                user=request.user,
                activity_type='updated',
                subject=f'Opportunity "{lead.title}" updated',
                description='Opportunity information was updated'
            )

            # Preserve navigation context on redirect
            redirect_url = f"{request.path}?view={view_context}&team={selected_team_id}"
            if selected_stage_id:
                redirect_url += f"&stage={selected_stage_id}"
            return redirect(redirect_url)
    else:
        form = LeadForm(instance=lead, user=request.user)

    # Build filtered leads queryset for navigation
    target_team = None
    if view_context == 'team':
        if request.user.is_sales_executive():
            if selected_team_id != 'all':
                try:
                    target_team = SalesTeam.objects.get(id=selected_team_id)
                except SalesTeam.DoesNotExist:
                    pass
        else:
            target_team = request.user.sales_team

    # Get leads based on view context
    if view_context == 'team':
        if selected_team_id == 'all' and request.user.is_sales_executive():
            nav_leads = Lead.objects.all()
        elif target_team:
            team_members = target_team.get_team_members()
            nav_leads = Lead.objects.filter(assigned_to__in=team_members)
        else:
            nav_leads = Lead.objects.filter(assigned_to=request.user)
    else:
        nav_leads = Lead.objects.filter(assigned_to=request.user)

    # Filter by stage if specified
    if selected_stage_id:
        try:
            nav_leads = nav_leads.filter(stage_id=int(selected_stage_id))
        except (ValueError, TypeError):
            pass

    # Order leads consistently and get prev/next
    nav_leads = nav_leads.order_by('-updated_at').values_list('id', flat=True)
    nav_lead_ids = list(nav_leads)

    prev_lead_id = None
    next_lead_id = None

    if lead.pk in nav_lead_ids:
        current_index = nav_lead_ids.index(lead.pk)
        if current_index > 0:
            prev_lead_id = nav_lead_ids[current_index - 1]
        if current_index < len(nav_lead_ids) - 1:
            next_lead_id = nav_lead_ids[current_index + 1]

    # Build navigation URLs with filter context
    nav_params = f"?view={view_context}&team={selected_team_id}"
    if selected_stage_id:
        nav_params += f"&stage={selected_stage_id}"

    # Get stages for the status bar based on user's team
    user_team = request.user.sales_team
    stages = LeadStage.get_stages_for_team(user_team)

    # Get all contacts for the contact selector, grouped by company
    contacts_by_company = {}

    # Group contacts by company and prioritize favorite contacts
    companies_with_contacts = Company.objects.filter(contacts__isnull=False).distinct()

    for company in companies_with_contacts:
        company_contacts = company.contacts.all()
        contact_list = []

        # Add favorite contact first if it exists
        if company.favorite_contact and company.favorite_contact in company_contacts:
            contact_list.append({
                'id': company.favorite_contact.id,
                'name': company.favorite_contact.name,
                'email': company.favorite_contact.email,
                'phone': company.favorite_contact.phone,
                'mobile': company.favorite_contact.mobile,
                'position': company.favorite_contact.position,
                'is_favorite': True,
            })
            # Add other contacts (excluding favorite)
            for contact in company_contacts.exclude(id=company.favorite_contact.id):
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })
        else:
            # No favorite contact, add all contacts
            for contact in company_contacts:
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })

        contacts_by_company[company.id] = contact_list

    # Get activities for this lead
    activities = Activity.objects.filter(lead=lead).select_related(
        'activity_type', 'assigned_to'
    ).order_by('-scheduled_date', '-created_at')

    # Get activity types for the quick add form
    from apps.activities.models import ActivityType
    activity_types = ActivityType.objects.filter(is_active=True)

    return render(request, 'crm/lead_form.html', {
        'form': form,
        'lead': lead,
        'stages': stages,
        'contacts_by_company_json': json.dumps(contacts_by_company),
        'selected_contact_id': form.selected_contact_id if hasattr(form, 'selected_contact_id') else '',
        'activities': activities,
        'activity_types': activity_types,
        'prev_lead_id': prev_lead_id,
        'next_lead_id': next_lead_id,
        'nav_params': nav_params,
        'current_lead_index': nav_lead_ids.index(lead.pk) + 1 if lead.pk in nav_lead_ids else 0,
        'total_leads_count': len(nav_lead_ids),
    })


@login_required
def lead_delete(request, pk):
    """Lead delete view"""
    lead = get_object_or_404(Lead, pk=pk)
    if not lead.can_be_edited_by(request.user):
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        raise Http404()

    if request.method == 'POST':
        lead_title = lead.title
        lead.delete()

        # Handle AJAX requests
        if request.content_type == 'application/json' or request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': True, 'message': f'Opportunity "{lead_title}" has been deleted.'})

        # Handle regular form requests
        return redirect('crm:opportunity_list')

    # GET request - show confirmation page for regular requests
    if request.content_type == 'application/json' or request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    return render(request, 'crm/lead_confirm_delete.html', {'lead': lead})


@login_required
def team_list(request):
    """Sales team list"""
    teams = SalesTeam.objects.filter(is_active=True)
    return render(request, 'crm/team_list.html', {'teams': teams})


@login_required
def team_detail(request, pk):
    """Sales team detail"""
    team = get_object_or_404(SalesTeam, pk=pk)
    return render(request, 'crm/team_detail.html', {'team': team})


@login_required
def team_create(request):
    """Sales team creation"""
    if not (request.user.is_sales_manager() or request.user.is_sales_executive()):
        messages.error(request, 'You do not have permission to create teams.')
        return redirect('crm:team_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        manager_id = request.POST.get('manager')
        is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'Team name is required.')
            return redirect('crm:team_create')

        # Get manager if specified
        manager = None
        if manager_id:
            try:
                manager = User.objects.get(id=manager_id)
            except User.DoesNotExist:
                messages.error(request, 'Selected manager not found.')
                return redirect('crm:team_create')

        # Create team
        team = SalesTeam.objects.create(
            name=name,
            description=description,
            manager=manager,
            is_active=is_active
        )

        return redirect('crm:team_detail', pk=team.pk)

    # Get potential managers (users with manager or executive roles)
    users = User.objects.filter(
        user_roles__role__name__in=['Sales Manager', 'Sales Executive'],
        is_active=True
    ).distinct().order_by('first_name', 'last_name', 'username')

    return render(request, 'crm/team_form.html', {'users': users})


@login_required
def team_edit(request, pk):
    """Sales team edit"""
    team = get_object_or_404(SalesTeam, pk=pk)

    if not (request.user.is_sales_manager() or request.user.is_sales_executive()):
        messages.error(request, 'You do not have permission to edit teams.')
        return redirect('crm:team_detail', pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        manager_id = request.POST.get('manager')
        is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'Team name is required.')
            return render(request, 'crm/team_form.html', {'team': team})

        # Get manager if specified
        manager = None
        if manager_id:
            try:
                manager = User.objects.get(id=manager_id)
            except User.DoesNotExist:
                messages.error(request, 'Selected manager not found.')
                return render(request, 'crm/team_form.html', {'team': team})

        # Update team
        team.name = name
        team.description = description
        team.manager = manager
        team.is_active = is_active
        team.save()

        return redirect('crm:team_detail', pk=team.pk)

    # Get potential managers (users with manager or executive roles)
    users = User.objects.filter(
        user_roles__role__name__in=['Sales Manager', 'Sales Executive'],
        is_active=True
    ).distinct().order_by('first_name', 'last_name', 'username')

    return render(request, 'crm/team_form.html', {'team': team, 'users': users})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_create_company(request):
    """API endpoint to create a new company"""
    try:
        data = json.loads(request.body)
        company_name = data.get('name', '').strip()

        if not company_name:
            return JsonResponse({'error': 'Company name is required'}, status=400)

        # Create company with auto-generated legal_id
        company = Company.objects.create(
            legal_name=company_name,
            legal_id=f'AUTO-{company_name.upper()[:10]}',
            created_by=request.user
        )

        return JsonResponse({
            'success': True,
            'company': {
                'id': company.id,
                'name': company.legal_name,
                'legal_id': company.legal_id
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_company_contacts(request, company_id):
    """API endpoint to get contacts for a company"""
    try:
        company = get_object_or_404(Company, id=company_id)

        # Get all contacts for the company
        all_contacts = company.contacts.all()

        # Prioritize favorite contact first, then other contacts
        contacts_ordered = []
        if company.favorite_contact and company.favorite_contact in all_contacts:
            # Add favorite contact first
            contacts_ordered.append(company.favorite_contact)
            # Add remaining contacts (excluding the favorite)
            contacts_ordered.extend(all_contacts.exclude(id=company.favorite_contact.id)[:4])
        else:
            # No favorite or favorite not found, use all contacts
            contacts_ordered = all_contacts[:5]

        contact_data = [
            {
                'id': contact.id,
                'name': contact.name,
                'email': contact.email,
                'phone': contact.phone,
                'mobile': contact.mobile,
                'position': contact.position,
                'is_favorite': contact == company.favorite_contact,
            }
            for contact in contacts_ordered
        ]

        company_data = {
            'id': company.id,
            'name': company.legal_name,
            'email': company.company_email,
            'phone': company.company_phone,
        }

        return JsonResponse({
            'company': company_data,
            'contacts': contact_data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_company_search(request):
    """API endpoint to search companies for autocomplete"""
    try:
        query = request.GET.get('q', '').strip()

        if not query or len(query) < 2:
            return JsonResponse({'companies': []})

        companies = Company.objects.filter(
            Q(legal_id__icontains=query) |
            Q(legal_name__icontains=query) |
            Q(brand_name__icontains=query)
        )[:10]  # Limit to 10 results

        company_data = [
            {
                'id': company.id,
                'name': company.brand_name or company.legal_name,
                'brand_name': company.brand_name,
                'legal_name': company.legal_name,
                'legal_id': company.legal_id,
            }
            for company in companies
        ]

        return JsonResponse({'companies': company_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Team-Specific Stage Management Views
@login_required
def team_stage_create(request, team_pk):
    """Create a stage for a specific team"""
    team = get_object_or_404(SalesTeam, pk=team_pk)

    # Check permissions
    if not (request.user.is_sales_executive() or
            (request.user.is_sales_manager() and team.manager == request.user)):
        messages.error(request, 'You do not have permission to manage stages for this team.')
        return redirect('crm:team_detail', pk=team_pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#6B7280').strip()
        probability = request.POST.get('probability', 0)
        is_closed_stage = request.POST.get('is_closed_stage') == 'on'

        if not name:
            messages.error(request, 'Stage name is required.')
            return redirect('crm:team_stage_create', team_pk=team_pk)

        try:
            probability = int(probability)
            if probability < 0 or probability > 100:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, 'Probability must be a number between 0 and 100.')
            return redirect('crm:team_stage_create', team_pk=team_pk)

        # Get next order number for this team
        from django.db import models
        existing_stages = LeadStage.objects.filter(sales_team=team)
        next_order = (existing_stages.aggregate(models.Max('order'))['order__max'] or 0) + 1

        try:
            stage = LeadStage.objects.create(
                name=name,
                description=description,
                color=color,
                probability=probability,
                is_closed_stage=is_closed_stage,
                sales_team=team,
                order=next_order,
                created_by=request.user
            )

            # Note: Migration is automatically handled by signals
            return redirect('crm:team_detail', pk=team_pk)

        except Exception as e:
            messages.error(request, f'Error creating stage: {str(e)}')
            return redirect('crm:team_stage_create', team_pk=team_pk)

    context = {
        'team': team,
    }

    return render(request, 'crm/team_stage_form.html', context)


@login_required
def team_stage_edit(request, team_pk, stage_pk):
    """Edit a team-specific stage"""
    team = get_object_or_404(SalesTeam, pk=team_pk)
    stage = get_object_or_404(LeadStage, pk=stage_pk, sales_team=team)

    # Check permissions
    if not stage.can_be_edited_by(request.user):
        messages.error(request, 'You do not have permission to edit this stage.')
        return redirect('crm:team_detail', pk=team_pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#6B7280').strip()
        probability = request.POST.get('probability', 0)
        is_closed_stage = request.POST.get('is_closed_stage') == 'on'

        if not name:
            messages.error(request, 'Stage name is required.')
            return render(request, 'crm/team_stage_form.html', {'team': team, 'stage': stage})

        try:
            probability = int(probability)
            if probability < 0 or probability > 100:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, 'Probability must be a number between 0 and 100.')
            return render(request, 'crm/team_stage_form.html', {'team': team, 'stage': stage})

        try:
            stage.name = name
            stage.description = description
            stage.color = color
            stage.probability = probability
            stage.is_closed_stage = is_closed_stage
            stage.save()

            return redirect('crm:team_detail', pk=team_pk)

        except Exception as e:
            messages.error(request, f'Error updating stage: {str(e)}')
            return render(request, 'crm/team_stage_form.html', {'team': team, 'stage': stage})

    context = {
        'team': team,
        'stage': stage,
    }

    return render(request, 'crm/team_stage_form.html', context)


@login_required
def team_stage_delete(request, team_pk, stage_pk):
    """Delete a team-specific stage"""
    team = get_object_or_404(SalesTeam, pk=team_pk)
    stage = get_object_or_404(LeadStage, pk=stage_pk, sales_team=team)

    # Check permissions
    if not stage.can_be_edited_by(request.user):
        messages.error(request, 'You do not have permission to delete this stage.')
        return redirect('crm:team_detail', pk=team_pk)

    # Check if stage has leads
    if stage.leads.exists():
        messages.error(request, f'Cannot delete stage "{stage.name}" because it contains leads. Move the leads to another stage first.')
        return redirect('crm:team_detail', pk=team_pk)

    if request.method == 'POST':
        stage_name = stage.name
        stage.delete()
        return redirect('crm:team_detail', pk=team_pk)

    context = {
        'team': team,
        'stage': stage,
    }

    return render(request, 'crm/team_stage_confirm_delete.html', context)


# ============================================
# Incoming Leads Views
# ============================================

@login_required
def incoming_lead_list(request):
    """List view for incoming leads"""
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    team_filter = request.GET.get('team', 'all')

    # Base queryset based on user permissions
    if request.user.is_sales_executive():
        leads = IncomingLead.objects.all()
    elif request.user.is_sales_manager() and request.user.sales_team:
        leads = IncomingLead.objects.filter(sales_team=request.user.sales_team)
    else:
        leads = IncomingLead.objects.filter(assigned_to=request.user)

    # Apply status filter
    if status_filter != 'all':
        leads = leads.filter(status=status_filter)

    # Apply team filter (for executives only)
    if request.user.is_sales_executive() and team_filter != 'all':
        try:
            team = SalesTeam.objects.get(id=team_filter)
            leads = leads.filter(sales_team=team)
        except (SalesTeam.DoesNotExist, ValueError):
            pass

    # Order by creation date (newest first)
    leads = leads.select_related('company', 'contact', 'sales_team', 'assigned_to', 'created_by').order_by('-created_at')

    # Get teams for filter dropdown (executives only)
    teams = SalesTeam.objects.filter(is_active=True) if request.user.is_sales_executive() else []

    context = {
        'leads': leads,
        'status_filter': status_filter,
        'team_filter': team_filter,
        'teams': teams,
        'status_choices': IncomingLead.STATUS_CHOICES,
    }

    return render(request, 'crm/incoming_lead_list.html', context)


@login_required
def incoming_lead_create(request):
    """Create new incoming lead"""
    if request.method == 'POST':
        form = IncomingLeadForm(request.POST, user=request.user)
        if form.is_valid():
            lead = form.save()
            messages.success(request, f'Lead created successfully.')
            return redirect('crm:lead_detail', pk=lead.pk)
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = IncomingLeadForm(user=request.user)

    # Get all companies for autocomplete
    companies = Company.objects.all()
    companies_list = [
        {
            'id': company.id,
            'legal_name': company.legal_name,
            'brand_name': company.brand_name,
            'legal_id': company.legal_id,
        }
        for company in companies
    ]

    # Get all contacts for the contact selector, grouped by company
    contacts_by_company = {}

    # Group contacts by company and prioritize favorite contacts
    companies_with_contacts = Company.objects.filter(contacts__isnull=False).distinct()

    for company in companies_with_contacts:
        company_contacts = company.contacts.all()
        contact_list = []

        # Add favorite contact first if it exists
        if company.favorite_contact and company.favorite_contact in company_contacts:
            contact_list.append({
                'id': company.favorite_contact.id,
                'name': company.favorite_contact.name,
                'email': company.favorite_contact.email,
                'phone': company.favorite_contact.phone,
                'mobile': company.favorite_contact.mobile,
                'position': company.favorite_contact.position,
                'is_favorite': True,
            })
            # Add other contacts (excluding favorite)
            for contact in company_contacts.exclude(id=company.favorite_contact.id):
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })
        else:
            # No favorite contact, add all contacts
            for contact in company_contacts:
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })

        contacts_by_company[company.id] = contact_list

    context = {
        'form': form,
        'action': 'Create Lead',
        'companies_json': json.dumps(companies_list),
        'contacts_by_company_json': json.dumps(contacts_by_company),
    }

    return render(request, 'crm/incoming_lead_form.html', context)


@login_required
def incoming_lead_detail(request, pk):
    """Detail view for incoming lead"""
    lead = get_object_or_404(IncomingLead, pk=pk)

    # Check permissions
    if not lead.can_be_viewed_by(request.user):
        raise Http404("Lead not found")

    context = {
        'lead': lead,
        'can_edit': lead.can_be_edited_by(request.user),
    }

    return render(request, 'crm/incoming_lead_detail.html', context)


@login_required
def incoming_lead_edit(request, pk):
    """Edit incoming lead"""
    lead = get_object_or_404(IncomingLead, pk=pk)

    # Check permissions
    if not lead.can_be_edited_by(request.user):
        messages.error(request, 'You do not have permission to edit this lead.')
        return redirect('crm:lead_detail', pk=lead.pk)

    if request.method == 'POST':
        form = IncomingLeadForm(request.POST, instance=lead, user=request.user)
        if form.is_valid():
            lead = form.save()
            messages.success(request, f'Lead updated successfully.')
            return redirect('crm:lead_detail', pk=lead.pk)
    else:
        form = IncomingLeadForm(instance=lead, user=request.user)

    # Get all companies for autocomplete
    companies = Company.objects.all()
    companies_list = [
        {
            'id': company.id,
            'legal_name': company.legal_name,
            'brand_name': company.brand_name,
            'legal_id': company.legal_id,
        }
        for company in companies
    ]

    # Get all contacts for the contact selector, grouped by company
    contacts_by_company = {}

    # Group contacts by company and prioritize favorite contacts
    companies_with_contacts = Company.objects.filter(contacts__isnull=False).distinct()

    for company in companies_with_contacts:
        company_contacts = company.contacts.all()
        contact_list = []

        # Add favorite contact first if it exists
        if company.favorite_contact and company.favorite_contact in company_contacts:
            contact_list.append({
                'id': company.favorite_contact.id,
                'name': company.favorite_contact.name,
                'email': company.favorite_contact.email,
                'phone': company.favorite_contact.phone,
                'mobile': company.favorite_contact.mobile,
                'position': company.favorite_contact.position,
                'is_favorite': True,
            })
            # Add other contacts (excluding favorite)
            for contact in company_contacts.exclude(id=company.favorite_contact.id):
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })
        else:
            # No favorite contact, add all contacts
            for contact in company_contacts:
                contact_list.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'mobile': contact.mobile,
                    'position': contact.position,
                    'is_favorite': False,
                })

        contacts_by_company[company.id] = contact_list

    context = {
        'form': form,
        'lead': lead,
        'action': 'Edit Lead',
        'companies_json': json.dumps(companies_list),
        'contacts_by_company_json': json.dumps(contacts_by_company),
    }

    return render(request, 'crm/incoming_lead_form.html', context)


@login_required
def incoming_lead_delete(request, pk):
    """Delete incoming lead"""
    lead = get_object_or_404(IncomingLead, pk=pk)

    # Check permissions
    if not lead.can_be_edited_by(request.user):
        messages.error(request, 'You do not have permission to delete this lead.')
        return redirect('crm:lead_detail', pk=lead.pk)

    if request.method == 'POST':
        # Get lead identifier for success message
        if lead.contact:
            lead_identifier = lead.contact.name
        elif lead.company:
            lead_identifier = lead.company.display_name
        else:
            lead_identifier = f"Lead #{lead.pk}"

        lead.delete()
        messages.success(request, f'Lead "{lead_identifier}" deleted successfully.')
        return redirect('crm:lead_list')

    context = {
        'lead': lead,
    }

    return render(request, 'crm/incoming_lead_confirm_delete.html', context)


@login_required
def incoming_lead_convert(request, pk):
    """Convert incoming lead to opportunity"""
    lead = get_object_or_404(IncomingLead, pk=pk)

    # Check permissions
    if not lead.can_be_edited_by(request.user):
        messages.error(request, 'You do not have permission to convert this lead.')
        return redirect('crm:lead_detail', pk=lead.pk)

    if lead.status == 'converted':
        messages.warning(request, 'This lead has already been converted.')
        if lead.converted_opportunity:
            return redirect('crm:opportunity_edit', pk=lead.converted_opportunity.pk)
        return redirect('crm:lead_detail', pk=lead.pk)

    if request.method == 'POST':
        # Get default stage for the team
        default_stage = LeadStage.get_default_stage_for_team(lead.sales_team)

        # Prepare opportunity title
        if lead.contact:
            title = f"Opportunity from {lead.contact.name}"
            full_name = lead.contact.name
            email = lead.contact.email
            phone = lead.contact.phone or lead.contact.mobile
            position = lead.contact.position
        elif lead.company:
            title = f"Opportunity from {lead.company.display_name}"
            full_name = ""
            email = lead.company.company_email or ""
            phone = lead.company.company_phone or ""
            position = ""
        else:
            title = "Opportunity from Lead"
            full_name = ""
            email = ""
            phone = ""
            position = ""

        # Create opportunity from lead
        opportunity = Lead.objects.create(
            title=title,
            full_name=full_name,
            email=email,
            phone=phone,
            position=position,
            company=lead.company,
            company_name=lead.company.legal_name if lead.company else "",
            contact=lead.contact,
            stage=default_stage,
            assigned_to=lead.assigned_to or request.user,
            sales_team=lead.sales_team,
            created_by=request.user,
            notes=f"Converted from incoming lead.\n\nOriginal Message:\n{lead.message}\n\n{lead.notes if lead.notes else ''}"
        )

        # Update lead status
        lead.status = 'converted'
        lead.converted_opportunity = opportunity
        lead.save()

        messages.success(request, f'Lead converted to opportunity successfully.')
        return redirect('crm:opportunity_edit', pk=opportunity.pk)

    context = {
        'lead': lead,
    }

    return render(request, 'crm/incoming_lead_confirm_convert.html', context)


# =============================================================================
# Lead Import Views
# =============================================================================

@login_required
def lead_import(request):
    """Lead import page - shows upload form, preview, or results based on session state"""
    # Handle cancel action - clear session and reset to upload state
    if request.GET.get('cancel') == '1':
        request.session.pop('lead_import_state', None)
        request.session.pop('lead_import_preview', None)
        request.session.pop('lead_import_results', None)
        return redirect('crm:opportunity_import')

    import_state = request.session.get('lead_import_state', 'upload')
    preview_data = request.session.get('lead_import_preview', None)
    import_results = request.session.get('lead_import_results', None)

    context = {
        'import_state': import_state,
        'preview_data': preview_data,
        'import_results': import_results,
    }

    # Clean up results state after displaying
    if import_state == 'results':
        request.session.pop('lead_import_state', None)
        request.session.pop('lead_import_results', None)

    return render(request, 'crm/lead_import.html', context)


@login_required
@require_http_methods(["POST"])
def lead_import_upload(request):
    """Handle Excel file upload and parse for preview"""
    from ..services.excel_import import parse_excel_file

    excel_file = request.FILES.get('excel_file')

    if not excel_file:
        messages.error(request, 'Please select an Excel file.')
        return redirect('crm:opportunity_import')

    if not excel_file.name.endswith('.xlsx'):
        messages.error(request, 'Only .xlsx files are supported.')
        return redirect('crm:opportunity_import')

    # Size limit: 5MB
    if excel_file.size > 5 * 1024 * 1024:
        messages.error(request, 'File size must be under 5MB.')
        return redirect('crm:opportunity_import')

    try:
        preview_data = parse_excel_file(excel_file, request.user)
        request.session['lead_import_state'] = 'preview'
        request.session['lead_import_preview'] = preview_data
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Error parsing file: {str(e)}')

    return redirect('crm:opportunity_import')


@login_required
@require_http_methods(["POST"])
def lead_import_confirm(request):
    """Process confirmed import from preview data"""
    from ..services.excel_import import execute_import

    preview_data = request.session.get('lead_import_preview')

    if not preview_data:
        messages.error(request, 'No import data found. Please upload again.')
        return redirect('crm:opportunity_import')

    results = execute_import(preview_data, request.user)

    # Clean up preview, set results
    request.session.pop('lead_import_preview', None)
    request.session['lead_import_state'] = 'results'
    request.session['lead_import_results'] = results

    return redirect('crm:opportunity_import')


@login_required
def lead_import_template(request):
    """Generate and download Excel import template"""
    from ..services.excel_template import generate_import_template

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="lead_import_template.xlsx"'

    wb = generate_import_template()
    wb.save(response)

    return response
