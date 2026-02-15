from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.crm.models import Lead, LeadStage, LeadActivity


class Command(BaseCommand):
    help = 'Migrate existing leads to ensure they have associated sales teams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Step 1: Assign sales teams to leads that don't have them
        leads_without_teams = Lead.objects.filter(sales_team__isnull=True)
        
        self.stdout.write(f'Found {leads_without_teams.count()} leads without sales teams')
        
        updated_count = 0
        for lead in leads_without_teams:
            if lead.assigned_to and lead.assigned_to.sales_team:
                if not dry_run:
                    lead.sales_team = lead.assigned_to.sales_team
                    lead.save(update_fields=['sales_team'])
                    
                self.stdout.write(f'  - Assigned lead "{lead.title}" to team "{lead.assigned_to.sales_team.name}"')
                updated_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  - Lead "{lead.title}" cannot be assigned (no team for user)')
                )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Updated {updated_count} leads with sales teams')
            )
        else:
            self.stdout.write(f'Would update {updated_count} leads with sales teams')
        
        # Step 2: Migrate leads to team-specific stages where appropriate
        teams_with_custom_stages = LeadStage.objects.filter(
            sales_team__isnull=False,
            is_active=True
        ).values_list('sales_team', flat=True).distinct()
        
        migration_count = 0
        for team_id in teams_with_custom_stages:
            if not dry_run:
                from apps.crm.models import SalesTeam
                team = SalesTeam.objects.get(id=team_id)
                
                # Count leads that would be migrated
                team_leads_on_global = Lead.objects.filter(
                    Q(sales_team=team) | Q(assigned_to__sales_team=team),
                    stage__sales_team__isnull=True,
                    stage__is_closed_stage=False
                )
                
                self.stdout.write(f'Migrating {team_leads_on_global.count()} leads for team "{team.name}"')
                
                LeadStage.migrate_leads_to_new_stages(team)
                migration_count += team_leads_on_global.count()
            else:
                from apps.crm.models import SalesTeam
                team = SalesTeam.objects.get(id=team_id)
                team_leads_on_global = Lead.objects.filter(
                    Q(sales_team=team) | Q(assigned_to__sales_team=team),
                    stage__sales_team__isnull=True,
                    stage__is_closed_stage=False
                )
                self.stdout.write(f'Would migrate {team_leads_on_global.count()} leads for team "{team.name}"')
                migration_count += team_leads_on_global.count()
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Migrated {migration_count} leads to team-specific stages')
            )
        else:
            self.stdout.write(f'Would migrate {migration_count} leads to team-specific stages')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('Lead migration completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Dry run completed. Use --dry-run=false to apply changes.')
            )