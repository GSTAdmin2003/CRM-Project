from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import LeadStage


@receiver(post_save, sender=LeadStage)
def handle_team_stage_created_or_updated(sender, instance, created, **kwargs):
    """
    When a team stage is created or updated, migrate leads from global stages
    to the team's custom stages based on closest probability match.
    """
    # Only trigger for team-specific stages (not global stages)
    if instance.sales_team and not instance.is_closed_stage:
        # Migrate leads to new team stages
        LeadStage.migrate_leads_to_new_stages(instance.sales_team)


@receiver(post_delete, sender=LeadStage)
def handle_team_stage_deleted(sender, instance, **kwargs):
    """
    When a team stage is deleted, migrate affected leads to remaining team stages
    or back to global stages if no team stages remain.
    """
    # Only trigger for team-specific stages (not global stages)
    # Use sales_team_id to avoid a DB lookup when the team may already be deleted (cascade).
    if instance.sales_team_id:
        from .models import Lead, LeadActivity
        from django.db.models import Q
        
        # Find leads that were on the deleted stage (use _id to avoid re-fetching deleted team)
        leads_on_deleted_stage = Lead.objects.filter(
            Q(sales_team_id=instance.sales_team_id) | Q(assigned_to__sales_team_id=instance.sales_team_id),
            stage=instance
        )

        # Get remaining team stages (excluding closed stages)
        remaining_team_stages = LeadStage.objects.filter(
            sales_team_id=instance.sales_team_id,
            is_active=True,
            is_closed_stage=False
        ).order_by('probability', 'order')
        
        for lead in leads_on_deleted_stage:
            if remaining_team_stages.exists():
                # Move to closest remaining team stage
                current_probability = lead.probability or 0
                closest_stage = min(
                    remaining_team_stages,
                    key=lambda stage: abs(stage.probability - current_probability)
                )
                
                lead.stage = closest_stage
                lead.probability = closest_stage.probability
                lead.save()
                
                # Log the migration
                LeadActivity.objects.create(
                    lead=lead,
                    user=None,
                    activity_type='stage_change',
                    subject=f'Auto-migrated to {closest_stage.name}',
                    description=f'Lead moved to "{closest_stage.name}" because stage "{instance.name}" was deleted'
                )
            else:
                # No team stages left, migrate back to global stages
                global_stages = LeadStage.objects.filter(
                    sales_team=None,
                    is_active=True,
                    is_closed_stage=False
                ).order_by('probability', 'order')
                
                if global_stages.exists():
                    current_probability = lead.probability or 0
                    closest_global_stage = min(
                        global_stages,
                        key=lambda stage: abs(stage.probability - current_probability)
                    )
                    
                    lead.stage = closest_global_stage
                    lead.probability = closest_global_stage.probability
                    lead.save()
                    
                    # Log the migration
                    LeadActivity.objects.create(
                        lead=lead,
                        user=None,
                        activity_type='stage_change',
                        subject=f'Auto-migrated to global stage {closest_global_stage.name}',
                        description=f'Lead moved to global stage "{closest_global_stage.name}" because team stage "{instance.name}" was deleted'
                    )