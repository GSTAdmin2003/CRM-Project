# CRM App

## Overview
The CRM app is the core business application — managing the sales pipeline with opportunities (leads), kanban board, sales teams, stages, incoming leads, and activity tracking. This is the largest app (~1450 line views.py).

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

### Lead (displayed as "Opportunity")
The core pipeline entity.
- Fields: `title`, `full_name`, `first_name`, `last_name`, `email`, `phone`, `company_name`, `position`, `estimated_value`, `probability`, `expected_close_date`, `source`, `status`, `custom_fields` (JSON), `notes`
- FKs: `stage` (LeadStage), `assigned_to` (User), `sales_team` (SalesTeam), `company` (contacts.Company), `contact` (contacts.Contact), `created_by` (User)
- Properties: `contact_full_name`, `weighted_value`
- Methods: `can_be_viewed_by()`, `can_be_edited_by()`

### LeadActivity
Activity log entries for opportunity timeline.
- Fields: `activity_type` (choices), `subject`, `description`, `duration`, `outcome`, `follow_up_date`
- FKs: `lead` (Lead), `user` (User)

### LeadFile
File attachments for opportunities.
- Fields: `file`, `filename`, `description`
- FKs: `lead` (Lead), `uploaded_by` (User)

### IncomingLead (displayed as "Lead")
Simple lead capture before conversion to opportunity.
- Fields: `message`, `status` (new/contacted/converted/rejected), `notes`
- FKs: `company`, `contact`, `sales_team`, `assigned_to`, `converted_opportunity` (Lead), `created_by`
- Methods: `can_be_viewed_by()`, `can_be_edited_by()`

## Cross-App Dependencies
- **Imports from**: `core.models.User`, `apps.contacts.models.Company`, `apps.contacts.models.Contact`
- **Imported by**: `apps.activities.models.Activity` (lead FK), `apps.calls.models.Call` (opportunity FK), `core.models.User` (sales_team FK, get_accessible_leads)

## Existing Services (Preserve)
- `services/excel_import.py` — bulk lead import
- `services/excel_template.py` — Excel template generation

## Target Services to Extract
- `LeadService` — CRUD, assignment, stage movement
- `KanbanService` — board data, stage updates, card reordering
- `TeamService` — team CRUD, member management
- `IncomingLeadService` — CRUD, conversion to opportunity
- `StageService` — CRUD, reordering, team-specific management

## Target API Endpoints
```
# Opportunities
GET    /crm/api/leads/                    — List opportunities
POST   /crm/api/leads/                    — Create opportunity
GET    /crm/api/leads/{id}/               — Opportunity detail
PUT    /crm/api/leads/{id}/               — Update opportunity
DELETE /crm/api/leads/{id}/               — Delete opportunity
GET    /crm/api/leads/kanban/             — Kanban board data
PATCH  /crm/api/leads/{id}/stage/         — Update opportunity stage

# Stages
GET    /crm/api/stages/                   — List stages
POST   /crm/api/stages/                   — Create stage

# Teams
GET    /crm/api/teams/                    — List teams
POST   /crm/api/teams/                    — Create team
GET    /crm/api/teams/{id}/               — Team detail

# Incoming Leads
GET    /crm/api/incoming-leads/           — List leads
POST   /crm/api/incoming-leads/           — Create lead
POST   /crm/api/incoming-leads/{id}/convert/ — Convert to opportunity
```
