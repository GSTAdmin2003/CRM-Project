"""
Template views -- existing Django views preserved during DRF transition.

These views render HTML templates. The old API-style function views
(api_kanban_data, api_update_lead_stage, etc.) are kept here for backward
compatibility with existing template JS code.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.activities.models import Activity
from apps.contacts.models import Company, Contact
from core.models import User

from ..models import Lead, LeadActivity, LeadStage, SalesTeam

from datetime import timedelta


@login_required
def crm_dashboard(request):
    """CRM main dashboard"""
    from django.core.serializers.json import DjangoJSONEncoder

    user_leads = request.user.get_accessible_leads_queryset()

    # Get this week's activities based on user role
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    week_activities = request.user.get_accessible_activities_queryset().filter(
        scheduled_date__gte=week_start,
        scheduled_date__lte=week_end
    ).select_related('activity_type', 'lead', 'assigned_to').order_by('scheduled_date', 'created_at')

    init_data = {
        "totalLeads": user_leads.count(),
        "totalValue": float(user_leads.aggregate(total=Sum('estimated_value'))['total'] or 0),
        "weekActivities": [
            {
                "id": a.id,
                "title": a.title,
                "scheduledDate": a.scheduled_date.isoformat() if a.scheduled_date else None,
                "leadTitle": a.lead.title if a.lead else None,
                "assignedTo": a.assigned_to.get_full_name() if a.assigned_to else None,
                "activityType": {
                    "name": a.activity_type.name,
                    "icon": a.activity_type.icon,
                    "color": a.activity_type.color,
                } if a.activity_type else None,
                "status": a.status,
            }
            for a in week_activities
        ],
        "apiUrls": {
            "leads": "/crm/api/leads/",
            "activities": "/activities/api/activities/",
            "teams": "/crm/api/teams/",
        },
    }

    return render(request, 'crm/dashboard.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


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


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_lead_quick_activity_create(request):
    """API endpoint for quick activity creation from lead form (alias for api_quick_activity_create)"""
    return api_quick_activity_create(request)


# Regular views (for non-API usage)
@login_required
def opportunity_list(request):
    """Opportunity list view — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    user_team = request.user.sales_team
    stages = LeadStage.get_stages_for_team(user_team)
    teams = SalesTeam.objects.filter(is_active=True) if request.user.is_sales_executive() else []

    init_data = {
        'isManager': request.user.is_sales_manager(),
        'isExecutive': request.user.is_sales_executive(),
        'stages': [{'id': s.id, 'name': s.name, 'color': s.color} for s in stages],
        'teams': [{'id': t.id, 'name': t.name} for t in teams],
        'apiUrls': {
            'leads': '/crm/api/leads/',
            'leadEdit': '/crm/opportunities/{id}/edit/',
            'leadDelete': '/crm/opportunities/{id}/delete/',
        },
    }
    return render(request, 'crm/lead_list.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def opportunity_create(request):
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

    # Individual companies: show their own data directly (no contact selection step)
    individual_companies = {}
    for company in Company.objects.filter(contact_type='individual'):
        individual_companies[company.id] = {
            'name': company.display_name,
            'email': company.company_email or '',
            'phone': company.company_phone or '',
            'mobile': company.company_mobile or '',
        }

    return render(request, 'crm/lead_form.html', {
        'form': form,
        'stages': stages,
        'contacts_by_company_json': json.dumps(contacts_by_company),
        'individual_companies_json': json.dumps(individual_companies),
        'selected_contact_id': form.selected_contact_id if hasattr(form, 'selected_contact_id') else '',
    })


def _resolve_wa_conversation_id(lead, lead_dict):
    """Return the WhatsApp conversation ID for a lead.

    Prefers the direct FK link. Falls back to a phone-number lookup so
    conversations started from the inbox still appear on the lead form.
    """
    conv_id = lead_dict.get('wa_conversation_id')
    if conv_id:
        return conv_id
    from apps.messaging.models import WhatsAppConversation
    from apps.messaging.services.helpers import normalize_phone
    contact = lead.contact
    phone = (contact.mobile or contact.phone) if contact else ""
    phone = phone or lead.phone
    if not phone:
        return None
    conv = WhatsAppConversation.objects.filter(phone_number=normalize_phone(phone)).first()
    return conv.pk if conv else None


@login_required
def opportunity_edit_redirect(request, pk):
    """Redirect stale URLs like /opportunities/2/edit/null to the correct edit URL."""
    return redirect("crm:opportunity_edit", pk=pk)


@login_required
def opportunity_edit(request, pk):
    """Lead/opportunity edit — serves Svelte shell with serialized initial data."""
    from django.core.serializers.json import DjangoJSONEncoder
    from rest_framework.renderers import JSONRenderer

    from apps.activities.models import ActivityType
    from apps.messaging.models import WhatsAppConversation

    from ..serializers import LeadDetailSerializer

    lead = get_object_or_404(Lead, pk=pk)
    if not lead.can_be_edited_by(request.user):
        raise Http404()

    view_context = request.GET.get('view', 'personal')
    selected_team_id = request.GET.get('team', 'all')
    selected_stage_id = request.GET.get('stage', '')

    # Build prev/next navigation
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

    if view_context == 'team':
        if selected_team_id == 'all' and request.user.is_sales_executive():
            nav_leads = Lead.objects.all()
        elif target_team:
            nav_leads = Lead.objects.filter(assigned_to__in=target_team.get_team_members())
        else:
            nav_leads = Lead.objects.filter(assigned_to=request.user)
    else:
        nav_leads = Lead.objects.filter(assigned_to=request.user)

    if selected_stage_id:
        try:
            nav_leads = nav_leads.filter(stage_id=int(selected_stage_id))
        except (ValueError, TypeError):
            pass

    nav_lead_ids = list(nav_leads.order_by('-updated_at').values_list('id', flat=True))

    prev_lead_id = next_lead_id = None
    if lead.pk in nav_lead_ids:
        idx = nav_lead_ids.index(lead.pk)
        if idx > 0:
            prev_lead_id = nav_lead_ids[idx - 1]
        if idx < len(nav_lead_ids) - 1:
            next_lead_id = nav_lead_ids[idx + 1]

    nav_params = f"?view={view_context}&team={selected_team_id}"
    if selected_stage_id:
        nav_params += f"&stage={selected_stage_id}"

    from apps.user_settings.models import UserPreferences
    user_lang = UserPreferences.get_or_create_for_user(request.user).language

    stages = LeadStage.get_stages_for_team(request.user.sales_team)
    activity_types = ActivityType.objects.filter(is_active=True)
    lead_dict = json.loads(JSONRenderer().render(LeadDetailSerializer(lead).data))

    init_data = {
        'leadId': lead.pk,
        'lead': lead_dict,
        'stages': [
            {'id': s.id, 'name': s.name, 'color': s.color,
             'probability': s.probability, 'is_closed_stage': s.is_closed_stage}
            for s in stages
        ],
        'activityTypes': [
            {'id': t.id, 'name': t.name, 'icon': t.icon, 'color': t.color}
            for t in activity_types
        ],
        'waConversationId': _resolve_wa_conversation_id(lead, lead_dict),
        'userLanguage': user_lang,
        'prevLeadId': prev_lead_id,
        'nextLeadId': next_lead_id,
        'navParams': nav_params,
        'currentIndex': nav_lead_ids.index(lead.pk) + 1 if lead.pk in nav_lead_ids else 0,
        'totalCount': len(nav_lead_ids),
        'apiUrls': {
            'lead': f'/crm/api/leads/{lead.pk}/',
            'leadStage': f'/crm/api/leads/{lead.pk}/stage/',
            'activities': '/activities/api/activities/',
            'activityTypes': '/activities/api/activity-types/',
            'conversations': '/messaging/api/conversations/',
            'templates': '/messaging/api/templates/',
            'companySearch': '/crm/api/company/search/',
        },
    }

    return render(request, 'crm/lead_form.html', {
        'lead': lead,
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def opportunity_delete(request, pk):
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
@require_http_methods(["POST"])
def send_sales_pitch(request, pk):
    """Send sales pitch PDF via WhatsApp for an opportunity"""
    lead = get_object_or_404(Lead, pk=pk)
    if not lead.can_be_edited_by(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('crm:opportunity_edit', pk=pk)

    try:
        from apps.messaging.services import WhatsAppService
        from core.exceptions import NotFoundError, ValidationError as ServiceValidationError
        WhatsAppService.send_sales_pitch(lead_id=pk, sent_by=request.user)
        messages.success(request, 'Sales pitch sent successfully via WhatsApp!')
    except (ServiceValidationError, Exception) as e:
        messages.error(request, str(e))

    return redirect('crm:opportunity_edit', pk=pk)


@login_required
def stage_list(request):
    """Pipeline stage list — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    stages_qs = LeadStage.objects.filter(is_active=True).order_by('order').select_related('sales_team')
    init_data = {
        "stages": [
            {
                "id": s.id,
                "name": s.name,
                "color": s.color,
                "probability": s.probability,
                "isClosedStage": s.is_closed_stage,
                "stageType": s.stage_type,
                "order": s.order,
                "teamName": s.sales_team.name if s.sales_team else None,
            }
            for s in stages_qs
        ],
        "apiUrls": {"stages": "/crm/api/stages/"},
    }
    return render(request, 'crm/stage_list.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def stage_create(request):
    """Pipeline stage create — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    init_data = {
        "stage": None,
        "teams": [{"id": t.id, "name": t.name} for t in SalesTeam.objects.filter(is_active=True)],
        "teamId": request.GET.get('team_id'),
        "apiUrls": {"stages": "/crm/api/stages/"},
    }
    return render(request, 'crm/stage_form.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def stage_edit(request, pk):
    """Pipeline stage edit — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    stage = get_object_or_404(LeadStage, pk=pk)
    init_data = {
        "stage": {
            "id": stage.id,
            "name": stage.name,
            "color": stage.color,
            "probability": stage.probability,
            "isClosedStage": stage.is_closed_stage,
            "order": stage.order,
            "salesTeamId": stage.sales_team.id if stage.sales_team else None,
        },
        "teams": [{"id": t.id, "name": t.name} for t in SalesTeam.objects.filter(is_active=True)],
        "teamId": request.GET.get('team_id'),
        "apiUrls": {"stages": "/crm/api/stages/"},
    }
    return render(request, 'crm/stage_form.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def team_list(request):
    """Sales team list — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder
    from apps.crm.models import LeadStage
    from apps.crm.services import TeamService

    teams = SalesTeam.objects.filter(is_active=True).order_by('name')
    can_manage_stages = (
        request.user.has_role('Sales Director')
        or request.user.has_role('Owner')
        or request.user.is_staff
    )
    global_stages = []
    if can_manage_stages:
        global_stages = [
            {
                "id": s.id,
                "name": s.name,
                "order": s.order,
                "color": s.color,
                "probability": s.probability,
                "isClosedStage": s.is_closed_stage,
                "stageType": s.stage_type,
                "description": s.description or "",
            }
            for s in LeadStage.objects.filter(sales_team=None, is_active=True).order_by('order')
        ]
    init_data = {
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "managerName": t.manager.get_full_name() if t.manager else None,
                "memberCount": t.get_team_members().count(),
            }
            for t in teams
        ],
        "canCreate": TeamService.can_manage(request.user),
        "canManageStages": can_manage_stages,
        "globalStages": global_stages,
        "apiUrls": {"teams": "/crm/api/teams/", "stages": "/crm/api/stages/"},
    }
    return render(request, 'crm/team_list.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def team_detail(request, pk):
    """Sales team detail — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    team = get_object_or_404(SalesTeam, pk=pk)
    members = team.get_team_members()
    from apps.crm.services import TeamService
    can_edit = TeamService.can_manage(request.user)
    all_users = User.objects.filter(is_active=True).order_by('first_name', 'last_name') if can_edit else []
    init_data = {
        "team": {
            "id": team.id,
            "name": team.name,
            "description": getattr(team, 'description', '') or '',
            "managerName": team.manager.get_full_name() if team.manager else None,
            "managerId": team.manager.id if team.manager else None,
        },
        "members": [
            {"id": m.id, "name": m.get_full_name(), "email": m.email}
            for m in members
        ],
        "allUsers": [{"id": u.id, "name": u.get_full_name()} for u in all_users],
        "canEdit": can_edit,
        "apiUrls": {
            "teams": "/crm/api/teams/",
            "stages": "/crm/api/stages/",
        },
    }
    return render(request, 'crm/team_detail.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def team_create(request):
    """Sales team creation — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder
    from apps.crm.services import TeamService

    if not TeamService.can_manage(request.user):
        messages.error(request, 'You do not have permission to create teams.')
        return redirect('crm:team_list')

    managers = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    init_data = {
        "team": None,
        "managers": [{"id": u.id, "name": u.get_full_name()} for u in managers],
        "apiUrls": {"teams": "/crm/api/teams/"},
    }
    return render(request, 'crm/team_form.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def team_edit(request, pk):
    """Sales team edit — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder
    from apps.crm.services import TeamService

    team = get_object_or_404(SalesTeam, pk=pk)

    if not TeamService.can_manage(request.user):
        messages.error(request, 'You do not have permission to edit teams.')
        return redirect('crm:team_detail', pk=pk)

    managers = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    init_data = {
        "team": {
            "id": team.id,
            "name": team.name,
            "description": getattr(team, 'description', '') or '',
            "managerId": team.manager.id if team.manager else None,
        },
        "managers": [{"id": u.id, "name": u.get_full_name()} for u in managers],
        "apiUrls": {"teams": "/crm/api/teams/"},
    }
    return render(request, 'crm/team_form.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


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
            'name': company.display_name,
            'email': company.company_email,
            'phone': company.company_phone or company.company_mobile,
            'contact_type': company.contact_type,
            'legal_id': company.legal_id,
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
        'init_data_json': json.dumps({
            'team': {'id': team.pk, 'name': team.name},
            'stage': None,
            'apiUrls': {'stages': '/crm/api/stages/'},
        }, cls=DjangoJSONEncoder),
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
        'init_data_json': json.dumps({
            'team': {'id': team.pk, 'name': team.name},
            'stage': {
                'id': stage.pk,
                'name': stage.name,
                'color': stage.color,
                'probability': stage.probability,
                'is_closed_stage': stage.is_closed_stage,
            },
            'apiUrls': {'stages': '/crm/api/stages/'},
        }, cls=DjangoJSONEncoder),
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

    from django.urls import reverse
    context = {
        'team': team,
        'stage': stage,
        'init_data_json': json.dumps({
            'title': f'Delete Stage — {team.name}',
            'message': f'This will permanently delete "{stage.name}" from {team.name}\'s pipeline. This cannot be undone.',
            'details': [
                {'label': 'Team', 'value': team.name},
                {'label': 'Stage', 'value': stage.name},
                {'label': 'Color', 'value': stage.color},
            ],
            'confirmLabel': 'Delete Stage',
            'confirmClass': 'bg-red-600 hover:bg-red-700',
            'cancelUrl': reverse('crm:team_detail', kwargs={'pk': team_pk}),
        }, cls=DjangoJSONEncoder),
    }

    return render(request, 'crm/team_stage_confirm_delete.html', context)


# ============================================
# Shared helpers
# ============================================

def _build_contacts_data():
    """Build contacts_by_company and individual_companies dicts for the lead form."""
    contacts_by_company = {}
    companies_with_contacts = Company.objects.filter(contacts__isnull=False).distinct()

    for company in companies_with_contacts:
        company_contacts = company.contacts.all()
        contact_list = []

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

    individual_companies = {}
    for company in Company.objects.filter(contact_type='individual'):
        individual_companies[company.id] = {
            'name': company.display_name,
            'email': company.company_email or '',
            'phone': company.company_phone or '',
            'mobile': company.company_mobile or '',
        }

    return contacts_by_company, individual_companies


# ============================================
# Lead Views (status='new')
# ============================================

@login_required
def lead_list(request):
    """Incoming lead list — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    teams = SalesTeam.objects.filter(is_active=True) if request.user.is_sales_executive() else []

    init_data = {
        'isManager': request.user.is_sales_manager(),
        'isExecutive': request.user.is_sales_executive(),
        'teams': [{'id': t.id, 'name': t.name} for t in teams],
        'statusChoices': Lead.STATUS_CHOICES,
        'apiUrls': {
            'leads': '/crm/api/leads/',
            'leadEdit': '/crm/leads/{id}/',
        },
    }
    return render(request, 'crm/incoming_lead_list.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def lead_create(request):
    """Create new lead — uses unified lead_form.html"""
    from ..forms import LeadForm
    if request.method == 'POST':
        form = LeadForm(request.POST, user=request.user)
        if form.is_valid():
            lead = form.save()
            messages.success(request, 'Lead created successfully.')
            return redirect('crm:lead_detail', pk=lead.pk)
    else:
        form = LeadForm(user=request.user)

    contacts_by_company, individual_companies = _build_contacts_data()
    stages = LeadStage.get_stages_for_team(request.user.sales_team)
    return render(request, 'crm/lead_form.html', {
        'form': form,
        'stages': stages,
        'contacts_by_company_json': json.dumps(contacts_by_company),
        'individual_companies_json': json.dumps(individual_companies),
        'selected_contact_id': form.selected_contact_id if hasattr(form, 'selected_contact_id') else '',
        'is_lead': True,
    })


@login_required
def lead_detail(request, pk):
    """Detail view for lead — renders Svelte shell."""
    from ..serializers.lead import LeadDetailSerializer

    lead = get_object_or_404(Lead, status="new", pk=pk)

    if not lead.can_be_viewed_by(request.user):
        raise Http404("Lead not found")

    serializer_data = LeadDetailSerializer(lead, context={'request': request}).data

    init_data = {
        'lead': dict(serializer_data),
        'apiUrls': {
            'lead': f'/crm/api/leads/{lead.pk}/',
            'leads': '/crm/api/leads/',
            'convertToOpportunity': f'/crm/api/leads/{lead.pk}/convert/',
            'leadEdit': f'/crm/leads/{lead.pk}/edit/',
        },
    }
    return render(request, 'crm/lead_detail.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def lead_edit(request, pk):
    """Lead edit — serves Svelte shell with serialized initial data."""
    from rest_framework.renderers import JSONRenderer
    from apps.activities.models import ActivityType
    from ..serializers import LeadDetailSerializer

    lead = get_object_or_404(Lead, status="new", pk=pk)
    if not lead.can_be_edited_by(request.user):
        raise Http404()

    # Build prev/next navigation among active leads only
    nav_leads = Lead.objects.filter(
        status="new", assigned_to=request.user
    ).order_by('-updated_at')
    nav_lead_ids = list(nav_leads.values_list('id', flat=True))

    prev_lead_id = next_lead_id = None
    if lead.pk in nav_lead_ids:
        idx = nav_lead_ids.index(lead.pk)
        if idx > 0:
            prev_lead_id = nav_lead_ids[idx - 1]
        if idx < len(nav_lead_ids) - 1:
            next_lead_id = nav_lead_ids[idx + 1]

    from apps.user_settings.models import UserPreferences
    user_lang = UserPreferences.get_or_create_for_user(request.user).language

    stages = LeadStage.get_stages_for_team(request.user.sales_team)
    activity_types = ActivityType.objects.filter(is_active=True)
    lead_dict = json.loads(JSONRenderer().render(LeadDetailSerializer(lead).data))

    init_data = {
        'leadId': lead.pk,
        'lead': lead_dict,
        'stages': [
            {'id': s.id, 'name': s.name, 'color': s.color,
             'probability': s.probability, 'is_closed_stage': s.is_closed_stage}
            for s in stages
        ],
        'activityTypes': [
            {'id': t.id, 'name': t.name, 'icon': t.icon, 'color': t.color}
            for t in activity_types
        ],
        'waConversationId': _resolve_wa_conversation_id(lead, lead_dict),
        'userLanguage': user_lang,
        'prevLeadId': prev_lead_id,
        'nextLeadId': next_lead_id,
        'navParams': '',
        'currentIndex': nav_lead_ids.index(lead.pk) + 1 if lead.pk in nav_lead_ids else 0,
        'totalCount': len(nav_lead_ids),
        'apiUrls': {
            'lead': f'/crm/api/leads/{lead.pk}/',
            'convert': f'/crm/api/leads/{lead.pk}/convert/',
            'leadStage': f'/crm/api/leads/{lead.pk}/stage/',
            'activities': '/activities/api/activities/',
            'activityTypes': '/activities/api/activity-types/',
            'conversations': '/messaging/api/conversations/',
            'templates': '/messaging/api/templates/',
            'companySearch': '/crm/api/company/search/',
        },
    }

    return render(request, 'crm/lead_form.html', {
        'lead': lead,
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def lead_delete(request, pk):
    """Delete lead"""
    lead = get_object_or_404(Lead, status="new", pk=pk)

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

    lead_name = lead.contact.name if lead.contact else (lead.company.display_name if lead.company else f'Lead #{lead.pk}')
    details = []
    if lead.contact:
        details.append({'label': 'Contact', 'value': lead.contact.name})
    if lead.company:
        details.append({'label': 'Company', 'value': lead.company.display_name})
    details.append({'label': 'Status', 'value': lead.get_status_display()})

    context = {
        'lead': lead,
        'init_data_json': json.dumps({
            'title': 'Delete Lead',
            'message': f'Are you sure you want to delete "{lead_name}"? This action cannot be undone.',
            'details': details,
            'confirmLabel': 'Delete Lead',
            'confirmClass': 'bg-red-600 hover:bg-red-700',
            'cancelUrl': f'/crm/leads/{lead.pk}/',
        }, cls=DjangoJSONEncoder),
    }

    return render(request, 'crm/incoming_lead_confirm_delete.html', context)


@login_required
def lead_convert(request, pk):
    """Convert lead to opportunity (legacy template-based view — API preferred)."""
    from ..services import LeadService
    from core.exceptions import ConflictError, ValidationError as ServiceValidationError

    lead = get_object_or_404(Lead, status="new", pk=pk)

    # Check permissions
    if not lead.can_be_edited_by(request.user):
        messages.error(request, 'You do not have permission to convert this lead.')
        return redirect('crm:lead_detail', pk=lead.pk)

    if request.method == 'POST':
        try:
            opportunity = LeadService.convert_lead_to_opportunity(
                lead=lead, user=request.user
            )
            messages.success(request, 'Lead converted to opportunity successfully.')
            return redirect('crm:opportunity_edit', pk=opportunity.pk)
        except (ConflictError, ServiceValidationError) as e:
            messages.error(request, str(e))
            return redirect('crm:lead_detail', pk=lead.pk)

    # GET — show confirmation page
    return render(request, 'crm/incoming_lead_confirm_convert.html', {'lead': lead})


# =============================================================================
# Lead Import Views
# =============================================================================

@login_required
def opportunity_import(request):
    """Lead import page — renders Svelte shell."""
    from django.core.serializers.json import DjangoJSONEncoder

    # Handle cancel action - clear session and reset to upload state
    if request.GET.get('cancel') == '1':
        request.session.pop('lead_import_state', None)
        request.session.pop('lead_import_preview', None)
        request.session.pop('lead_import_results', None)
        return redirect('crm:opportunity_import')

    init_data = {
        "apiUrls": {
            "upload": "/crm/opportunities/import/upload/",
            "confirm": "/crm/opportunities/import/confirm/",
            "template": "/crm/opportunities/import/template/",
        },
    }
    return render(request, 'crm/lead_import.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
@require_http_methods(["POST"])
def opportunity_import_upload(request):
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
def opportunity_import_confirm(request):
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
@require_http_methods(["POST"])
def opportunities_bulk_action(request):
    """Bulk action on opportunities"""
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')

    if not selected_ids:
        messages.warning(request, 'No opportunities selected.')
        return redirect('crm:opportunity_list')

    leads = Lead.objects.filter(
        id__in=selected_ids, status="converted"
    )

    if action == 'delete':
        count = leads.count()
        leads.delete()
        messages.success(request, f'{count} opportunity(ies) deleted successfully.')
    else:
        messages.warning(request, 'Unknown action.')

    return redirect('crm:opportunity_list')


@login_required
@require_http_methods(["POST"])
def leads_bulk_action(request):
    """Bulk action on leads"""
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')

    if not selected_ids:
        messages.warning(request, 'No leads selected.')
        return redirect('crm:lead_list')

    leads = Lead.objects.filter(
        id__in=selected_ids, status="new"
    )

    if action == 'delete':
        count = leads.count()
        leads.delete()
        messages.success(request, f'{count} lead(s) deleted successfully.')
    else:
        messages.warning(request, 'Unknown action.')

    return redirect('crm:lead_list')


@login_required
def opportunity_import_template(request):
    """Generate and download Excel import template"""
    from ..services.excel_template import generate_import_template

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="lead_import_template.xlsx"'

    wb = generate_import_template()
    wb.save(response)

    return response
