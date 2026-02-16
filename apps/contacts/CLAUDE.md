# Contacts App

## Overview
The Contacts app manages companies and their contacts. Companies have a "favorite contact" feature, and the app supports Excel import/export of company data.

## Models

### Company
Represents a business entity.
- Fields: `legal_id` (unique), `legal_name`, `brand_name`, `company_phone`, `company_mobile`, `company_email`, `industry`, `category`, timestamps
- FKs: `favorite_contact` (Contact, nullable), `created_by` (User), `updated_by` (User)
- Key methods: `display_name` (property), `set_default_favorite_contact()`, `ensure_favorite_contact()`
- Auto-behavior: first contact auto-becomes favorite

### Contact
A person associated with a company.
- Fields: `name`, `position`, `email`, `phone`, `mobile`, timestamps
- FK: `company` (Company, CASCADE)
- Signal: `set_favorite_contact_on_create` — auto-sets first contact as favorite

## Business Rules
- Every company has a unique `legal_id`
- Companies can have a "favorite" contact — auto-assigned to first contact if not set
- Excel import supports bulk company creation
- `display_name` returns `brand_name` if set, otherwise `legal_name`

## Cross-App Dependencies
- **Imports from**: `core.models.User`
- **Imported by**: `apps.crm.models.Lead` (company FK, contact FK), `apps.calls.models.Call` (contact FK)

## Existing Services (Preserve)
- `services/excel_import.py` — bulk company import from Excel
- `services/excel_template.py` — Excel template generation

## Target API Endpoints
```
GET    /contacts/api/companies/                — List companies
POST   /contacts/api/companies/                — Create company
GET    /contacts/api/companies/{id}/           — Company detail
PUT    /contacts/api/companies/{id}/           — Update company
DELETE /contacts/api/companies/{id}/           — Delete company
GET    /contacts/api/companies/{id}/contacts/  — List contacts for company
POST   /contacts/api/contacts/                 — Create contact
GET    /contacts/api/contacts/{id}/            — Contact detail
PUT    /contacts/api/contacts/{id}/            — Update contact
DELETE /contacts/api/contacts/{id}/            — Delete contact
POST   /contacts/api/companies/{id}/toggle-favorite/{contact_id}/ — Toggle favorite
```
