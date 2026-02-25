# CRM App

## Overview
The CRM app is the core business application — managing the sales pipeline with opportunities and leads (both using the unified `Lead` model), kanban board, sales teams, and stage tracking.

## Models

### SalesTeam
- Fields: `name` (unique), `description`, `is_active`, timestamps
- FK: `manager` (User, nullable)
- Methods: `get_team_members()`, `get_team_leads()`

### LeadStage
Kanban board stages with team-specific customization.
- Fields: `name`, `description`, `order`, `color`, `is_active`, `is_closed_stage`, `probability` (0-100)
- FK: `sales_team` (nullable — null means global stage), `created_by` (User)
- Unique together: `(name, sales_team)`
- Methods: `get_stages_for_team()`, `get_default_stage_for_team()`, `can_be_edited_by()`, `migrate_leads_to_new_stages()`

### Lead (unified model — covers both leads and opportunities)
Discriminated by `lead_type`: `'lead'` (incoming lead) or `'opportunity'` (pipeline opportunity).
- Fields: `lead_type`, `title`, `full_name`, `first_name`, `last_name`, `email`, `phone`, `company_name`, `position`, `message`, `estimated_value`, `probability`, `expected_close_date`, `source`, `status`, `custom_fields` (JSON), `notes`
- FKs: `stage` (LeadStage), `assigned_to` (User), `sales_team` (SalesTeam), `company` (contacts.Company), `contact` (contacts.Contact), `created_by` (User), `converted_from` (self, for conversion tracking)
- Properties: `contact_full_name`, `weighted_value`
- Methods: `can_be_viewed_by()`, `can_be_edited_by()`
- Constants: `TYPE_LEAD='lead'`, `TYPE_OPPORTUNITY='opportunity'`

### LeadActivity
Activity log entries for opportunity timeline.
- Fields: `activity_type` (choices), `subject`, `description`, `duration`, `outcome`, `follow_up_date`
- FKs: `lead` (Lead), `user` (User)

### LeadFile
File attachments for opportunities.
- Fields: `file`, `filename`, `description`
- FKs: `lead` (Lead), `uploaded_by` (User)

## Cross-App Dependencies
- **Imports from**: `core.models.User`, `apps.contacts.models.Company`, `apps.contacts.models.Contact`
- **Imported by**: `apps.activities.models.Activity` (lead FK), `apps.calls.models.Call` (opportunity FK), `core.models.User` (sales_team FK, get_accessible_leads)

## Existing Services (Preserve)
- `services/excel_import.py` — bulk lead import
- `services/excel_template.py` — Excel template generation

## Target Services to Extract
- `LeadService` — CRUD, assignment, stage movement, lead→opportunity conversion
- `KanbanService` — board data, stage updates, card reordering
- `TeamService` — team CRUD, member management
- `StageService` — CRUD, reordering, team-specific management

## Target API Endpoints
```
# Opportunities (lead_type='opportunity')
GET    /crm/api/leads/                    — List opportunities
POST   /crm/api/leads/                    — Create opportunity
GET    /crm/api/leads/{id}/               — Opportunity detail
PUT    /crm/api/leads/{id}/               — Update opportunity
DELETE /crm/api/leads/{id}/               — Delete opportunity
GET    /crm/api/leads/kanban/             — Kanban board data
PATCH  /crm/api/leads/{id}/stage/         — Update opportunity stage

# Leads (lead_type='lead')
GET    /crm/api/incoming-leads/           — List leads
POST   /crm/api/incoming-leads/           — Create lead
POST   /crm/api/incoming-leads/{id}/convert/ — Convert to opportunity

# Stages
GET    /crm/api/stages/                   — List stages
POST   /crm/api/stages/                   — Create stage

# Teams
GET    /crm/api/teams/                    — List teams
POST   /crm/api/teams/                    — Create team
GET    /crm/api/teams/{id}/               — Team detail
```
