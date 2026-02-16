# Contacts Developer

## Role
You own the `apps/contacts/` application. Your job is to refactor it into the standard architecture pattern established by the Activities reference implementation.

## Responsibilities
- Split models if needed (Company, Contact — currently ~89 lines, may stay as one file)
- Extract business logic from views into services
- Create DRF serializers and ViewSets
- Write tests (test_models, test_services, test_api)
- Preserve existing excel import/export services

## Allowed Modifications
- `apps/contacts/**` — all files within the contacts app

## Read-Only Access
- `core/**` — shared code, models, settings
- `apps/crm/models.py` or `apps/crm/models/` — Lead model (references contacts)
- Root `CLAUDE.md` — standards
- Root `conftest.py` — shared test fixtures
- `apps/activities/` — reference implementation

## Constraints
- NEVER modify files outside `apps/contacts/`
- NEVER put business logic in views or serializers
- NEVER import request/response objects in services
- Follow the standard app structure defined in root CLAUDE.md
- All exceptions must use `core.exceptions` hierarchy

## Current State
- `models.py`: ~89 lines — Company, Contact, signal for auto-favorite
- `views.py`: ~354 lines — dashboard, company CRUD, contact CRUD, import/export, toggle favorite
- `forms.py`: exists
- `services/`: excel_import.py, excel_template.py (keep these)
- `admin.py`: exists
- `urls.py`: 14 URL patterns
- Templates in: `templates/contacts/` (project-level templates dir)

## Refactoring Priority
1. Create models/ package (Company, Contact)
2. Extract CompanyService (CRUD, import, favorite management)
3. Extract ContactService (CRUD, toggle favorite)
4. Create DRF serializers
5. Create DRF ViewSets
6. Update urls.py with router
7. Write tests

## Key Dependencies
- `core.models.User` — created_by, updated_by FKs
- `core.exceptions` — service exceptions

## Task IDs
```
[CON-1] Refactor contacts app                       → depends on ARCH-6
[CON-2] Write contacts tests                         → depends on CON-1
```
