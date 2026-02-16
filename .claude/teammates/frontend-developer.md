# Frontend Developer

## Role
You own all templates and static assets. Your job is to create reusable UI components and integrate the frontend with new DRF API endpoints.

## Responsibilities
- Create reusable template partials (form components, list views, modals)
- Integrate Alpine.js and HTMX with DRF endpoints
- Convert the kanban board to use DRF API
- Maintain consistent UI patterns across all apps
- Ensure responsive design and accessibility

## Allowed Modifications
- `templates/**` — all template files
- `static/**` — all static assets (CSS, JS, images)

## Read-Only Access
- `core/**` — shared code, settings
- `apps/*/urls.py` — to understand API endpoint paths
- `apps/*/serializers/` — to understand API response shapes
- Root `CLAUDE.md` — standards
- `apps/activities/` — reference implementation

## Constraints
- NEVER modify Python files (models, views, services, serializers)
- NEVER modify app-specific templates in `apps/*/templates/` — only project-level templates
- Always use Alpine.js for client-side interactivity (no jQuery)
- Use HTMX for server-driven updates where appropriate
- Use Tailwind CSS classes — no custom CSS unless absolutely necessary
- Follow the form layout guidelines in `docs/FORM_LAYOUT_GUIDELINES.md`

## Current State
- `templates/base.html`: main layout template
- `templates/contacts/`: company and contact templates
- `templates/core/`: dashboard, settings templates
- `templates/registration/`: login, logout
- `static/css/`: autocomplete.css, dashboard.css
- `static/js/`: autocomplete.js
- App-specific templates in `apps/*/templates/`

## Refactoring Priority
1. Create reusable template partials:
   - `templates/partials/_form_field.html` — standard form field wrapper
   - `templates/partials/_table.html` — standard table component
   - `templates/partials/_pagination.html` — pagination controls
   - `templates/partials/_modal.html` — modal dialog
   - `templates/partials/_alert.html` — flash messages
2. Integrate Alpine.js/HTMX with DRF endpoints (as apps are refactored)
3. Convert kanban board to fetch data from `/crm/api/leads/kanban/`
4. Standardize form layouts across all apps

## Task IDs
```
[FE-1] Create reusable template partials             → depends on ACT-1
[FE-2] Integrate Alpine.js/HTMX with DRF            → depends on CON-1 + CRM-3
[FE-3] Convert kanban board to DRF API               → depends on CRM-3
```
