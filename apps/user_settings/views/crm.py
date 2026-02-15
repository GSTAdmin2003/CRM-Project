from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import models

from apps.crm.models import LeadStage


@login_required
def global_stages_view(request):
    """Global pipeline stages management"""
    # Check permissions - only owners and sales executives can manage global stages
    if not (request.user.has_role('Owner') or request.user.is_sales_executive()):
        messages.error(request, 'You do not have permission to manage global pipeline stages.')
        return redirect('settings:home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            return _handle_create_stage(request)
        elif action == 'update':
            return _handle_update_stage(request)
        elif action == 'delete':
            return _handle_delete_stage(request)
    
    # Get global stages
    global_stages = LeadStage.objects.filter(sales_team=None, is_active=True).order_by('order')
    
    context = {
        'current_section': 'crm',
        'current_page': 'global_stages',
        'global_stages': global_stages,
    }
    
    return render(request, 'settings/crm/global_stages.html', context)


def _handle_create_stage(request):
    """Handle creation of a new global stage"""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    color = request.POST.get('color', '#6B7280').strip()
    probability = request.POST.get('probability', 0)
    is_closed_stage = request.POST.get('is_closed_stage') == 'on'
    
    if not name:
        messages.error(request, 'Stage name is required.')
        return redirect('settings:crm:global_stages')
    
    try:
        probability = int(probability)
        if probability < 0 or probability > 100:
            raise ValueError()
    except (ValueError, TypeError):
        messages.error(request, 'Probability must be a number between 0 and 100.')
        return redirect('settings:crm:global_stages')
    
    # Get next order number for global stages
    existing_stages = LeadStage.objects.filter(sales_team=None)
    next_order = (existing_stages.aggregate(models.Max('order'))['order__max'] or 0) + 1
    
    try:
        stage = LeadStage.objects.create(
            name=name,
            description=description,
            color=color,
            probability=probability,
            is_closed_stage=is_closed_stage,
            sales_team=None,  # Global stage
            order=next_order,
            created_by=request.user
        )
        
        messages.success(request, f'Global pipeline stage "{stage.name}" created successfully.')
    except Exception as e:
        messages.error(request, f'Error creating stage: {str(e)}')
    
    return redirect('settings:crm:global_stages')


def _handle_update_stage(request):
    """Handle updating an existing global stage"""
    stage_id = request.POST.get('stage_id')
    if not stage_id:
        messages.error(request, 'Invalid stage ID.')
        return redirect('settings:crm:global_stages')
    
    try:
        stage = LeadStage.objects.get(pk=stage_id, sales_team=None)
    except LeadStage.DoesNotExist:
        messages.error(request, 'Stage not found.')
        return redirect('settings:crm:global_stages')
    
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    color = request.POST.get('color', '#6B7280').strip()
    probability = request.POST.get('probability', 0)
    is_closed_stage = request.POST.get('is_closed_stage') == 'on'
    
    if not name:
        messages.error(request, 'Stage name is required.')
        return redirect('settings:crm:global_stages')
    
    try:
        probability = int(probability)
        if probability < 0 or probability > 100:
            raise ValueError()
    except (ValueError, TypeError):
        messages.error(request, 'Probability must be a number between 0 and 100.')
        return redirect('settings:crm:global_stages')
    
    try:
        stage.name = name
        stage.description = description
        stage.color = color
        stage.probability = probability
        stage.is_closed_stage = is_closed_stage
        stage.save()
        
        messages.success(request, f'Global pipeline stage "{stage.name}" updated successfully.')
    except Exception as e:
        messages.error(request, f'Error updating stage: {str(e)}')
    
    return redirect('settings:crm:global_stages')


def _handle_delete_stage(request):
    """Handle deletion of a global stage"""
    stage_id = request.POST.get('stage_id')
    if not stage_id:
        messages.error(request, 'Invalid stage ID.')
        return redirect('settings:crm:global_stages')
    
    try:
        stage = LeadStage.objects.get(pk=stage_id, sales_team=None)
    except LeadStage.DoesNotExist:
        messages.error(request, 'Stage not found.')
        return redirect('settings:crm:global_stages')
    
    # Check if stage has leads
    if stage.leads.exists():
        messages.error(request, f'Cannot delete stage "{stage.name}" because it contains leads. Move the leads to another stage first.')
        return redirect('settings:crm:global_stages')
    
    stage_name = stage.name
    stage.delete()
    messages.success(request, f'Global pipeline stage "{stage_name}" deleted successfully.')
    
    return redirect('settings:crm:global_stages')


# URL patterns for CRM settings
from django.urls import path

crm_urls = [
    path('global-stages/', global_stages_view, name='global_stages'),
]