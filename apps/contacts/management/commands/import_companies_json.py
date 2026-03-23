"""
Management command to bulk-import companies from companies.json.

The JSON supports two entry formats:

  List format (legacy):
    key → [legal_id, legal_name, '', '', mobile, email, industry, category,
            contact_name_or_email, '', contact_phone, contact_mobile, ...]

  Dict format (structured):
    key → {id, sk, co, mo, ph, em, em2, br, ind, cat, c: [[pos, name, email, phone], ...]}

Usage:
  python manage.py import_companies_json
  python manage.py import_companies_json --json /path/to/companies.json
  python manage.py import_companies_json --dry-run
"""

import hashlib
import json
import logging
import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.db import transaction

from apps.contacts.models import Company, Contact

logger = logging.getLogger(__name__)


def _first_phone(val: str) -> str:
    """Return the first phone number when a field contains comma/semicolon-separated list."""
    if not val:
        return ''
    # Split on common separators and return the first non-empty token
    for sep in (',', ';', '/'):
        if sep in val:
            val = val.split(sep)[0].strip()
            break
    return val


def _is_email(val: str) -> bool:
    try:
        validate_email(val)
        return True
    except ValidationError:
        return False


def _safe_str(val, default='') -> str:
    return str(val).strip() if val else default


def _parse_list_entry(hash_key: str, row: list) -> dict | None:
    """Parse old array-format entry. Returns parsed dict or None to skip."""

    def get(idx):
        return _safe_str(row[idx] if idx < len(row) else None)

    legal_id = get(0) or f'IMPORT-{hash_key[:16]}'
    legal_name = get(1)
    if not legal_name:
        return None

    raw_mobile = _first_phone(get(4))
    raw_email = get(5)
    raw_industry = get(6)   # often 'construction', 'F&B', or a CRM note
    raw_category = get(7)   # sub-industry / category
    raw_field8 = get(8)     # contact name OR email
    raw_field10 = get(10)   # contact phone
    raw_field11 = get(11)   # contact mobile

    # If [5] is empty and [8] looks like an email, promote it to company email
    company_email = raw_email
    contact_name = raw_field8
    if not company_email and _is_email(raw_field8):
        company_email = raw_field8
        contact_name = ''

    contacts = []
    if contact_name and not _is_email(contact_name):
        contacts.append({
            'name': contact_name,
            'position': '',
            'email': '',
            'phone': raw_field10,
            'mobile': raw_field11,
        })

    return {
        'legal_id': legal_id,
        'legal_name': legal_name,
        'brand_name': '',
        'company_phone': '',
        'company_mobile': raw_mobile,
        'company_email': company_email,
        'industry': raw_industry,
        'category': raw_category,
        'contacts': contacts,
    }


def _parse_dict_entry(hash_key: str, row: dict) -> dict | None:
    """Parse structured dict-format entry. Returns parsed dict or None to skip."""
    legal_id = _safe_str(row.get('sk')) or f'IMPORT-{hash_key[:16]}'
    legal_name = _safe_str(row.get('co'))

    contacts_raw = row.get('c') or []

    # Fallback: use first contact name as company name when co is absent
    if not legal_name and contacts_raw:
        first = contacts_raw[0]
        if isinstance(first, list) and len(first) > 1:
            legal_name = _safe_str(first[1])

    if not legal_name:
        return None

    # Company email: first valid value from em / em2
    company_email = ''
    for key in ('em', 'em2'):
        val = _safe_str(row.get(key))
        if val and val != '-' and _is_email(val):
            company_email = val
            break

    # Phones (some entries have comma-separated multiple numbers — take the first)
    company_mobile = _first_phone(_safe_str(row.get('mo')))
    company_phone = _first_phone(_safe_str(row.get('ph')))

    # Contacts: each entry is [position, name, email, phone]
    contacts = []
    for c in contacts_raw:
        if not isinstance(c, list) or len(c) < 2:
            continue
        name = _safe_str(c[1] if len(c) > 1 else None)
        if not name:
            continue
        position = _safe_str(c[0] if len(c) > 0 else None)
        email_raw = _safe_str(c[2] if len(c) > 2 else None)
        email = email_raw if _is_email(email_raw) else ''
        mobile = _first_phone(_safe_str(c[3] if len(c) > 3 else None))
        contacts.append({
            'name': name,
            'position': position,
            'email': email,
            'phone': '',
            'mobile': mobile,
        })

    return {
        'legal_id': legal_id,
        'legal_name': legal_name,
        'brand_name': _safe_str(row.get('br')),
        'company_phone': company_phone,
        'company_mobile': company_mobile,
        'company_email': company_email,
        'industry': _safe_str(row.get('ind')),
        'category': _safe_str(row.get('cat')),
        'contacts': contacts,
    }


def _parse_flat_entry(row: dict) -> dict | None:
    """
    Parse companies_full.json flat format:
      {company_id, company_name, brand_name, mobile, phone, email, industry, category,
       director, director_mobile, director_phone,
       accountant, accountant_mobile,
       manager, manager_mobile, manager_phone}
    """
    legal_id = _safe_str(row.get('company_id'))
    legal_name = _safe_str(row.get('company_name'))
    if not legal_name:
        return None

    if not legal_id:
        # Stable hash from company name as fallback
        legal_id = 'IMPORT-' + hashlib.md5(legal_name.lower().encode()).hexdigest()[:16]

    contacts = []
    for name_key, pos_label, mob_key, phone_key in [
        ('director',   'Director',   'director_mobile',   'director_phone'),
        ('accountant', 'Accountant', 'accountant_mobile', None),
        ('manager',    'Manager',    'manager_mobile',    'manager_phone'),
    ]:
        name = _safe_str(row.get(name_key))
        # Skip blanks or strings that look like CRM notes (> 50 chars)
        if not name or len(name) > 50:
            continue
        mob = _first_phone(_safe_str(row.get(mob_key) if mob_key else None))
        ph  = _first_phone(_safe_str(row.get(phone_key) if phone_key else None))
        email_raw = _safe_str(row.get('email')) if name_key == 'director' else ''
        email = email_raw if _is_email(email_raw) else ''
        contacts.append({'name': name, 'position': pos_label, 'email': email, 'phone': ph, 'mobile': mob})

    company_email = _safe_str(row.get('email'))
    if not _is_email(company_email):
        company_email = ''

    return {
        'legal_id': legal_id,
        'legal_name': legal_name,
        'brand_name': _safe_str(row.get('brand_name')),
        'company_phone': _first_phone(_safe_str(row.get('phone'))),
        'company_mobile': _first_phone(_safe_str(row.get('mobile'))),
        'company_email': company_email,
        'industry': _safe_str(row.get('industry')),
        'category': _safe_str(row.get('category')),
        'contacts': contacts,
    }


class Command(BaseCommand):
    help = 'Import companies (and their contacts) from companies.json into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            dest='json_path',
            default=os.path.join(settings.BASE_DIR, 'companies.json'),
            help='Path to companies.json (default: <BASE_DIR>/companies.json)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and report statistics without writing to the database',
        )

    def handle(self, *args, **options):
        json_path = options['json_path']
        dry_run = options['dry_run']

        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f'File not found: {json_path}'))
            return

        self.stdout.write(f'Loading {json_path} ...')
        with open(json_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        # Parse all entries — support two file shapes:
        #   flat list:  [{company_name, company_id, ...}, ...]   (companies_full format)
        #   hash dict:  {hash: [...] or {...}, ...}              (companies / companies2 format)
        parsed = []
        skipped_no_name = 0

        if isinstance(raw, list):
            self.stdout.write(f'  Format: flat list ({len(raw)} entries)')
            for row in raw:
                if not isinstance(row, dict):
                    continue
                entry = _parse_flat_entry(row)
                if entry is None:
                    skipped_no_name += 1
                else:
                    parsed.append(entry)
        else:
            version = raw.pop('__version__', None)
            if version:
                self.stdout.write(f'  File version: {version}')
            list_count = dict_count = 0
            for hash_key, value in raw.items():
                if isinstance(value, list):
                    list_count += 1
                    entry = _parse_list_entry(hash_key, value)
                elif isinstance(value, dict):
                    dict_count += 1
                    entry = _parse_dict_entry(hash_key, value)
                else:
                    continue
                if entry is None:
                    skipped_no_name += 1
                else:
                    parsed.append(entry)
            self.stdout.write(
                f'  Format: hash-keyed dict ({list_count} list + {dict_count} dict entries)'
            )

        # Deduplicate by legal_id: keep first occurrence
        seen_ids: set[str] = set()
        deduped = []
        duplicates = 0
        for entry in parsed:
            lid = entry['legal_id']
            if lid in seen_ids:
                duplicates += 1
            else:
                seen_ids.add(lid)
                deduped.append(entry)

        total_contacts = sum(len(e['contacts']) for e in deduped)

        self.stdout.write(f'  Skipped (no name): {skipped_no_name}')
        self.stdout.write(f'  Duplicates removed: {duplicates}')
        self.stdout.write(f'  To import: {len(deduped)} companies, {total_contacts} contacts')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDry run — no data written.'))
            return

        self.stdout.write('\nImporting ...')
        stats = {
            'companies_created': 0,
            'companies_skipped': 0,
            'contacts_created': 0,
            'errors': 0,
        }

        for i, entry in enumerate(deduped, 1):
            try:
                with transaction.atomic():
                    company, created = Company.objects.get_or_create(
                        legal_id=entry['legal_id'][:100],
                        defaults={
                            'legal_name': entry['legal_name'][:200],
                            'brand_name': entry['brand_name'][:200],
                            'company_phone': entry['company_phone'][:20],
                            'company_mobile': entry['company_mobile'][:20],
                            'company_email': entry['company_email'][:254],
                            'industry': entry['industry'][:100],
                            'category': entry['category'][:100],
                            'created_by': None,
                            'updated_by': None,
                        },
                    )

                    if created:
                        stats['companies_created'] += 1
                    else:
                        stats['companies_skipped'] += 1
                        continue  # Don't add duplicate contacts to existing companies

                    for c in entry['contacts']:
                        Contact.objects.create(
                            company=company,
                            name=c['name'][:200],
                            position=c['position'][:100],
                            email=c['email'][:254],
                            phone=c['phone'][:20],
                            mobile=c['mobile'][:20],
                        )
                        stats['contacts_created'] += 1

            except Exception as exc:
                stats['errors'] += 1
                logger.warning('Failed to import entry %s: %s', entry['legal_id'], exc)

            if i % 1000 == 0:
                self.stdout.write(f'  ... {i}/{len(deduped)}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone!\n'
            f'  Companies created : {stats["companies_created"]}\n'
            f'  Already existed   : {stats["companies_skipped"]}\n'
            f'  Contacts created  : {stats["contacts_created"]}\n'
            f'  Errors            : {stats["errors"]}'
        ))
