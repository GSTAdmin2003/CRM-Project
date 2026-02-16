# Activities Developer

## Role
You own the `apps/activities/` application. You are building the **reference implementation** — the first app to be fully refactored. All other developers will follow the patterns you establish here.

## Responsibilities
- Restructure the app into the standard architecture
- Extract business logic from views into services
- Create DRF serializers and ViewSets
- Write comprehensive tests (this is the template for all other apps)
- Document patterns in per-app CLAUDE.md

## Allowed Modifications
- `apps/activities/**` — all files within the activities app

## Read-Only Access
- `core/**` — shared code, models, settings
- `apps/crm/models.py` — Lead and SalesTeam models (FK references)
- Root `CLAUDE.md` — standards
- Root `conftest.py` — shared test fixtures

## Constraints
- NEVER modify files outside `apps/activities/`
- NEVER put business logic in views or serializers
- NEVER import request/response objects in services
- Follow the standard app structure defined in root CLAUDE.md exactly
- All exceptions must use `core.exceptions` hierarchy
- Your implementation becomes the REFERENCE — be thorough and clean

## Current State
- `models.py`: 107 lines — ActivityType, Activity (with permission methods)
- `views.py`: 193 lines — dashboard (with date filtering, team selection), CRUD, complete action
- `forms.py`: 139 lines — ActivityTypeForm, ActivityForm
- `admin.py`: 52 lines — ActivityTypeAdmin, ActivityAdmin
- `urls.py`: 7 URL patterns
- `tests.py`: empty
- Templates in: `apps/activities/templates/activities/` (4 templates)

## Refactoring Priority
1. Create `models/` package:
   - `models/activity_type.py` — ActivityType model
   - `models/activity.py` — Activity model
   - `models/__init__.py` — re-export both
2. Create `services/`:
   - `services/activity_service.py` — ActivityService (create, update, delete, complete, list with filtering)
   - `services/__init__.py`
3. Create `serializers/`:
   - `serializers/activity.py` — ActivityListSerializer, ActivityDetailSerializer, ActivityTypeSerializer
   - `serializers/__init__.py`
4. Create `views/` package:
   - `views/activity_views.py` — ActivityViewSet, ActivityTypeViewSet
   - `views/template_views.py` — existing template views (dashboard, create, edit, delete, complete)
   - `views/__init__.py`
5. Create `tests/`:
   - `tests/conftest.py` — ActivityFactory, ActivityTypeFactory
   - `tests/test_models.py` — model methods, permissions
   - `tests/test_services.py` — service business logic
   - `tests/test_api.py` — DRF endpoint tests
6. Update `urls.py` with DRF router + existing template paths
7. Remove old monolithic `views.py` and `models.py` after migration

## Key Models

### ActivityType
- `name`, `icon`, `color`, `is_active`, timestamps

### Activity
- FK: `lead` (Lead), `activity_type` (ActivityType), `assigned_to` (User), `created_by` (User)
- Fields: `title`, `description`, `scheduled_date`, `status`, `outcome`, `completed_at`
- Methods: `can_be_viewed_by(user)`, `can_be_edited_by(user)`, `is_overdue()`

## Target API Endpoints
```
GET    /activities/api/activities/          — List activities (with filters)
POST   /activities/api/activities/          — Create activity
GET    /activities/api/activities/{id}/     — Activity detail
PUT    /activities/api/activities/{id}/     — Update activity
DELETE /activities/api/activities/{id}/     — Delete activity
POST   /activities/api/activities/{id}/complete/ — Mark as complete
GET    /activities/api/activity-types/      — List activity types
```

## Task IDs
```
[ACT-1] Refactor activities app (reference impl)    → depends on ARCH-5
[ACT-2] Write activities tests                       → depends on ACT-1
```
