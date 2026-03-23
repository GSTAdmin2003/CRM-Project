import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Pull daily leads from Partner Portal and create Leads in CRM'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Print what would be imported without saving')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        portal_url = getattr(settings, 'PARTNER_PORTAL_URL', None)
        api_token = getattr(settings, 'PARTNER_API_TOKEN', None)

        if not portal_url or not api_token:
            self.stderr.write(self.style.ERROR(
                'PARTNER_PORTAL_URL and PARTNER_API_TOKEN must be set in settings.'
            ))
            return

        url = f"{portal_url}/api/v1/leads/daily/"
        self.stdout.write(f"Pulling leads from {url}...")

        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Token {api_token}"},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"Failed to fetch leads: {exc}"))
            return

        data = resp.json()
        companies = data.get('companies', [])
        meta = data.get('meta', {})
        self.stdout.write(f"Received {meta.get('total', len(companies))} companies.")

        if dry_run:
            for company in companies:
                self.stdout.write(f"  [dry-run] Would import: {company.get('name')} ({company.get('country', '')})")
            return

        created_leads = 0
        created_companies = 0
        created_contacts = 0

        with transaction.atomic():
            for company_data in companies:
                result = self._import_company(company_data)
                created_companies += result['companies']
                created_contacts += result['contacts']
                created_leads += result['leads']

        self.stdout.write(self.style.SUCCESS(
            f"Import complete: {created_companies} companies, "
            f"{created_contacts} contacts, {created_leads} leads."
        ))

    def _import_company(self, company_data: dict) -> dict:
        """Import one company + its contacts as a Lead in the CRM."""
        from apps.contacts.models import Contact
        from apps.crm.models import Lead

        company_name = company_data.get('name', '').strip()
        if not company_name:
            return {'companies': 0, 'contacts': 0, 'leads': 0}

        # Get or create company-type Contact
        company, company_created = Contact.objects.get_or_create(
            type=Contact.TYPE_COMPANY,
            legal_name=company_name,
            defaults={},
        )

        contacts_created = 0
        for contact_data in company_data.get('contacts', []):
            contact_name = contact_data.get('name', '').strip()
            if not contact_name:
                continue
            Contact.objects.get_or_create(
                type=Contact.TYPE_INDIVIDUAL,
                parent_company=company,
                name=contact_name,
                defaults={
                    'email': contact_data.get('email', ''),
                    'mobile': contact_data.get('mobile', ''),
                    'position': contact_data.get('job_title', ''),
                },
            )
            contacts_created += 1

        # Create a Lead for this company if not already existing
        lead_created = 0
        if not Lead.objects.filter(company=company, status='new').exists():
            Lead.objects.create(
                title=company_name,
                company=company,
                status='new',
            )
            lead_created = 1

        return {
            'companies': 1 if company_created else 0,
            'contacts': contacts_created,
            'leads': lead_created,
        }
