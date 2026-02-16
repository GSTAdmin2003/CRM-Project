# User Settings App

## Overview
The User Settings app provides a centralized settings interface for user profiles, general system settings, CRM configuration, and VoIP settings.

## Current Status: ENABLED
Fixed in SET-1:
- `apps.py` name corrected to `apps.user_settings`
- SIPSettings duplication resolved (canonical model in `apps.calls`)
- Missing directories created: `services/`, `serializers/`, `tests/`
- Re-enabled in INSTALLED_APPS
- Migration 0002 still creates then 0003 (pending) will remove the duplicate SIPSettings table

## Models (Already Split)

### Base models (`models/base.py`)
- `BaseSettingModel` — abstract base with created_at/updated_at
- `SettingsCategory` — sidebar categories
- `SettingsPage` — individual settings pages

### Profile models (`models/profile.py`)
- `UserPreferences` — theme, language, timezone, notifications, dashboard layout

### General models (`models/general.py`)
- `SystemConfiguration` — key/value system settings with typed values

### VoIP
SIPSettings lives in `apps.calls.models` — imported directly by views/forms.

## Views (Already Split)
- `views/base.py` — base view utilities (SettingsBaseMixin)
- `views/profile.py` — profile settings views
- `views/general.py` — general settings views
- `views/crm.py` — CRM-specific settings (global stages)
- `views/voip.py` — VoIP settings views (imports SIPSettings from calls app)

## Cross-App Dependencies
- **Imports from**: `core.models.User`, `apps.crm.models.LeadStage`, `apps.calls.models.SIPSettings`
- **Imported by**: core URLs reference settings views, init_settings management command
