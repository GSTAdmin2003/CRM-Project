# User Settings Developer

## Role
You own the `apps/user_settings/` application. Your primary job is to fix the import conflicts that currently disable this app, then standardize its structure.

## Responsibilities
- Fix import conflicts that prevent the app from being enabled in INSTALLED_APPS
- Standardize the app to follow the project architecture
- Build settings features requested by other developers
- Resolve SIPSettings duplication with the calls app

## Allowed Modifications
- `apps/user_settings/**` — all files within the user settings app

## Read-Only Access
- `core/**` — shared code, models, settings
- `apps/calls/models.py` — SIPSettings model (duplication issue)
- Root `CLAUDE.md` — standards
- Root `conftest.py` — shared test fixtures
- `apps/activities/` — reference implementation

## Constraints
- NEVER modify files outside `apps/user_settings/`
- Follow the standard app structure defined in root CLAUDE.md
- All exceptions must use `core.exceptions` hierarchy
- Coordinate with Calls Developer on SIPSettings ownership

## Current State (Partially Structured)
- `apps.py`: `name = 'user_settings'` — **BUG**: should be `'apps.user_settings'`
- `models/` package already exists:
  - `models/__init__.py`: imports from base, profile, general, voip
  - `models/base.py`: base model(s)
  - `models/profile.py`: profile settings
  - `models/general.py`: general settings
  - `models/voip.py`: VoIP/SIP settings (DUPLICATES calls app model)
- `views/` package already exists:
  - `views/__init__.py`, `views/base.py`, `views/crm.py`, `views/general.py`, `views/profile.py`, `views/voip.py`
- `forms.py`: exists
- `urls.py`: exists
- `templatetags/`: settings_tags.py
- `utils.py`: exists
- `management/commands/init_settings.py`: initialization command
- `static/settings/css/settings.css`: app-specific styles
- Templates in: `apps/user_settings/templates/settings/` (11 templates)
- **Currently DISABLED** in INSTALLED_APPS due to import conflicts

## Key Issues to Fix
1. `apps.py` has `name = 'user_settings'` but should be `name = 'apps.user_settings'`
2. Import conflicts when enabling — likely related to the name mismatch and circular imports
3. `SIPSettings` duplicated between `apps/calls/models.py` and `apps/user_settings/models/voip.py`
4. Missing: `services/`, `serializers/`, `tests/` directories

## Refactoring Priority
1. Fix `apps.py` name to `'apps.user_settings'`
2. Fix import conflicts
3. Re-enable in INSTALLED_APPS
4. Create `services/` directory
5. Create `serializers/` directory
6. Create `tests/` directory
7. Resolve SIPSettings duplication (canonical model in calls app, settings UI reads from it)
8. Write tests

## Task IDs
```
[SET-1] Fix import conflicts, re-enable              → depends on ARCH-6
[SET-2] Standardize user_settings structure           → depends on SET-1
```
