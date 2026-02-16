# CRM Project — Development Standards

> This document is the single source of truth for all development patterns.
> Every teammate (Architect, App Developers, Frontend Developer) MUST follow these rules.

## Tech Stack

- **Backend**: Django 5.1.4, Python 3.12
- **Database**: PostgreSQL 15
- **Cache/Broker**: Redis 7
- **Async Tasks**: Celery 5.3
- **VoIP**: Asterisk (ARI)
- **API**: Django REST Framework 3.15
- **Frontend**: Django templates, Alpine.js, HTMX, Tailwind CSS
- **Testing**: pytest, pytest-django, factory_boy
- **Code Quality**: black, isort, flake8, mypy, pre-commit

---

## Standard App Structure

Every app under `apps/` MUST follow this layout:

```
apps/<app>/
  __init__.py
  apps.py                      # AppConfig with name = "apps.<app>"
  admin.py
  urls.py
  models/
    __init__.py                # Re-exports all models
    <entity>.py                # One file per model group
  services/
    __init__.py
    <entity>_service.py        # Business logic (stateless, no HTTP objects)
  serializers/
    __init__.py
    <entity>.py                # DRF serializers
  views/
    __init__.py
    <entity>_views.py          # DRF ViewSets / APIViews
    template_views.py          # Legacy Django template views (kept during transition)
  tests/
    __init__.py
    conftest.py                # App-specific factories (factory_boy)
    test_models.py
    test_services.py
    test_api.py
  migrations/
  CLAUDE.md                    # App-specific developer guide
```

---

## Service Layer Rules

1. **All business logic lives in `services/`** — never in views or serializers.
2. Services are **stateless**: use `@staticmethod` or `@classmethod`.
3. Services use **keyword-only arguments** (`*`) for clarity.
4. Services raise exceptions from `core.exceptions` — never HTTP exceptions.
5. Services use `@transaction.atomic` for multi-step DB operations.
6. Services **never import** `request`, `response`, or any HTTP object.

```python
# Example service method
from django.db import transaction
from core.exceptions import NotFoundError, ValidationError

class LeadService:
    @staticmethod
    @transaction.atomic
    def create_lead(*, title: str, company_id: int, stage_id: int,
                    created_by: "User", **kwargs) -> "Lead":
        # ... business logic ...
        # Raises: ValidationError, NotFoundError
```

---

## Exception Hierarchy (`core/exceptions.py`)

```
ServiceError (base)
├── NotFoundError
├── PermissionDeniedError
├── ValidationError
└── ConflictError
```

Views catch these and translate:
- `NotFoundError` → 404
- `PermissionDeniedError` → 403
- `ValidationError` → 400
- `ConflictError` → 409

---

## DRF Conventions

### Settings (`REST_FRAMEWORK` in `core/settings.py`)

- **Authentication**: SessionAuthentication (existing auth model)
- **Default Permission**: IsAuthenticated
- **Pagination**: PageNumberPagination, page_size=25
- **Filters**: DjangoFilterBackend, SearchFilter, OrderingFilter

### Patterns

- `ModelViewSet` for standard CRUD.
- `APIView` for custom endpoints (e.g., VoIP calls, stage reordering).
- Separate `ListSerializer` / `DetailSerializer` when field sets differ.
- FK writes: `<field>_id` via `PrimaryKeyRelatedField`.
- FK reads: nested serializer representation.
- URL routing: DRF `DefaultRouter` in each app's `urls.py`.
- All API endpoints under the `api/` prefix within each app.
- No API versioning (internal app, frontend+backend deploy together).

```python
# apps/<app>/urls.py pattern
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import lead_views, template_views

router = DefaultRouter()
router.register(r'leads', lead_views.LeadViewSet, basename='lead')

app_name = '<app>'
urlpatterns = [
    path('api/', include(router.urls)),             # New DRF endpoints
    path('', template_views.dashboard, name='dashboard'),  # Existing views kept
]
```

---

## Model Rules

- Every model declares `class Meta: app_label = 'apps.<app>'` OR the AppConfig sets `name = 'apps.<app>'`.
- `created_at = DateTimeField(auto_now_add=True)` and `updated_at = DateTimeField(auto_now=True)` on all models.
- Foreign keys to User: `settings.AUTH_USER_MODEL` or `'core.User'`.
- Use `on_delete=models.PROTECT` for critical references, `SET_NULL` for optional.

---

## Testing Standards

- **Framework**: pytest + pytest-django + factory_boy
- **Coverage target**: 60% on critical paths (services, API views)
- **Required tests per app**: `test_models.py`, `test_services.py`, `test_api.py`
- **Naming**: `test_<what>_<condition>_<expected_result>` (e.g., `test_create_lead_missing_title_raises_validation_error`)
- **API tests**: Use DRF's `APIClient` via the `api_client` fixture in root `conftest.py`.
  **Important**: Use `api_client.force_login(user)` (not `force_authenticate`) because `RoleBasedAccessMiddleware` checks `request.user.is_authenticated` at the Django middleware layer before DRF authentication runs.
- **Factories**: Use `factory_boy` in `apps/<app>/tests/conftest.py`

---

## Coding Standards

- **Formatter**: black (line-length 99)
- **Import sort**: isort (Django profile)
- **Linter**: flake8 (max-line-length 99)
- **Type checker**: mypy (django-stubs, drf-stubs)
- Run `pre-commit run --all-files` before committing.

---

## Security Rules

- `ALLOWED_HOSTS` is set via environment variable — never `['*']`.
- No `@csrf_exempt` on views — DRF handles CSRF via SessionAuthentication.
- All API endpoints require `IsAuthenticated` at minimum.
- Sensitive data (passwords, tokens) must be encrypted at rest.
- No secrets in code or version control.

---

## Cross-App Communication

- **Reading**: Any app can `from apps.<other_app>.models import Model` for read access.
- **Writing**: Only the owning app's service should modify its own models.
- **Shared code**: All shared utilities go in `core/` — only the Architect writes to `core/`.
- **Settings features**: Request from User Settings Developer, don't build your own.

---

## Git Conventions

- Branch naming: `<task-id>/<short-description>` (e.g., `ACT-1/refactor-activities`)
- Commit messages: `[TASK-ID] Short imperative description`
- One logical change per commit.
- Never commit `.env`, credentials, or large binary files.

---

## File Naming

- Python: `snake_case.py`
- Templates: `snake_case.html`
- CSS/JS: `snake_case.css` / `snake_case.js`
- Model files: named after the primary model (e.g., `lead.py` for `Lead` model)
- Service files: `<entity>_service.py`
- View files: `<entity>_views.py`

---

## Task Dependencies

Developers MUST claim tasks in order. See the task board for current assignments and dependencies. A task cannot start until all its dependencies are marked complete by the Architect.

### Task Prefixes

| Prefix | Owner |
|---|---|
| `ARCH-N` | Architect |
| `ACT-N` | Activities Developer |
| `CON-N` | Contacts Developer |
| `CRM-N` | CRM Developer |
| `CALL-N` | Calls Developer |
| `SET-N` | User Settings Developer |
| `FE-N` | Frontend Developer |

---

## Architecture Validation

Run before marking any app complete:

```bash
python manage.py validate_architecture apps/<app>/
```

All apps must pass with zero errors.
