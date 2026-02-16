# Calls App

## Overview
The Calls app handles VoIP integration with Asterisk via ARI (Asterisk REST Interface). It manages call initiation, tracking, recording, and SIP credential management.

## Models

### Call
Tracks individual VoIP calls.
- Fields: `asterisk_channel_id` (unique), `asterisk_uniqueid`, `direction` (inbound/outbound), `status` (initiated/ringing/answered/ended/failed/busy/no_answer), `from_number`, `to_number`, `duration`, `started_at`, `answered_at`, `ended_at`, `notes`, timestamps
- FKs: `contact` (contacts.Contact), `opportunity` (crm.Lead), `user` (User)
- Properties: `duration_formatted`

### CallRecording
One-to-one with Call for audio recordings.
- Fields: `file` (FileField), `duration`, `file_size`, timestamps
- Properties: `file_size_formatted`

### CallLog
Event log tracking all state changes for a call.
- Fields: `event`, `data` (JSON), `timestamp`
- FK: `call` (Call)

### SIPSettings
Per-user SIP credentials with encrypted passwords.
- Fields: `server_ip`, `server_port`, `username`, `_password` (encrypted), `caller_id`, `is_active`, `registration_status`, `last_registration_check`, timestamps
- FK: `user` (User, OneToOne)
- Password property with encrypt/decrypt

## Key Modules
- `ari_client.py` — Asterisk ARI REST client
- `ari_events.py` — WebSocket event handler for real-time call events
- `asterisk_config.py` — Dynamic Asterisk configuration
- `encryption.py` — Password encryption/decryption utilities
- `tasks.py` — Celery tasks (cleanup_old_recordings, sync_asterisk_recordings, update_call_statistics)

## Cross-App Dependencies
- **Imports from**: `core.models.User`, `apps.contacts.models.Contact`, `apps.crm.models.Lead`
- **Imported by**: None directly (calls are linked via FKs)

## Important Notes
- Real-time VoIP endpoints must use `APIView`, not `ModelViewSet` — latency matters
- Always mock ARI client in tests
- SIP passwords are encrypted at rest using `encryption.py`
- Celery Beat runs periodic tasks for recording cleanup, sync, and statistics

## Target API Endpoints
```
GET    /calls/api/calls/                — List calls
GET    /calls/api/calls/{id}/           — Call detail
POST   /calls/api/calls/initiate/       — Initiate outbound call
POST   /calls/api/calls/{id}/hangup/    — Hang up call
POST   /calls/api/calls/{id}/answer/    — Answer call
GET    /calls/api/calls/{id}/status/    — Call status
PATCH  /calls/api/calls/{id}/notes/     — Update call notes
GET    /calls/api/calls/active/         — Active calls list
GET    /calls/api/recordings/{id}/      — Download recording
```
