# Activities App

## Overview
The Activities app tracks scheduled activities (calls, meetings, emails, etc.) linked to CRM opportunities (leads). It provides a dashboard with date filtering and team-based visibility.

## Models

### ActivityType
Defines types of activities with visual customization.
- Fields: `name`, `icon` (Font Awesome class), `color` (hex), `is_active`, timestamps
- Used by: Activity (FK)

### Activity
A scheduled activity linked to an opportunity.
- Fields: `title`, `description`, `scheduled_date`, `status` (planned/completed/cancelled), `outcome`, `completed_at`
- FKs: `lead` (crm.Lead), `activity_type` (ActivityType), `assigned_to` (User), `created_by` (User)
- Key methods: `can_be_viewed_by(user)`, `can_be_edited_by(user)`, `is_overdue()`

## Business Rules
- Activities are always linked to an opportunity (lead)
- Permission model: Executives see all, Managers see their team's, Reps see their own
- Completing an activity records the completion timestamp and optional outcome
- Dashboard supports date filters: today, week, next_week, future, past, custom, range
- Team view is restricted to managers and executives

## Cross-App Dependencies
- **Imports from**: `apps.crm.models.Lead`, `apps.crm.models.SalesTeam`, `core.models.User`
- **Imported by**: `core.models.User.get_accessible_activities_queryset()`

## Target API Endpoints
```
GET    /activities/api/activities/          — List (filterable by date, team, status)
POST   /activities/api/activities/          — Create
GET    /activities/api/activities/{id}/     — Detail
PUT    /activities/api/activities/{id}/     — Update
DELETE /activities/api/activities/{id}/     — Delete
POST   /activities/api/activities/{id}/complete/  — Mark complete
GET    /activities/api/activity-types/      — List activity types
```
