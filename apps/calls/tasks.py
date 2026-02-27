"""
Celery tasks for call processing
"""
import os
import subprocess
import logging
from django.core.files import File
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    from celery.exceptions import Retry as CeleryRetry
except ImportError:
    # Celery not installed - create a dummy decorator
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    CeleryRetry = type('CeleryRetry', (Exception,), {})


@shared_task(bind=True, max_retries=5)
def process_recording(self, call_id):
    """
    Process and import recording from Asterisk.

    This task:
    1. Locates the WAV recording in Asterisk's recording directory
    2. Converts it to MP3 for smaller file size
    3. Creates a CallRecording record with the file
    4. Cleans up temporary files

    Retries up to 5 times with a 30-second delay because Asterisk writes
    the MixMonitor file after the call ends — we may arrive before it's ready.
    """
    import glob as _glob
    from .models import Call, CallRecording

    try:
        call = Call.objects.get(id=call_id)

        # Check if recording already exists
        if hasattr(call, 'recording') and call.recording:
            logger.info(f"Recording already exists for call {call_id}")
            return

        # Recording path in Asterisk (MixMonitor default: /var/spool/asterisk/monitor)
        recordings_path = getattr(
            settings,
            'ASTERISK_RECORDINGS_PATH',
            '/var/spool/asterisk/monitor'
        )

        # Build candidate filenames.  The dialplan uses MixMonitor(${UNIQUEID}.wav)
        # where ${UNIQUEID} == the ARI channel id stored in asterisk_channel_id.
        # asterisk_uniqueid is a legacy field that may be empty — skip it when blank.
        candidates = []
        if call.asterisk_channel_id:
            candidates.append(f"{call.asterisk_channel_id}.wav")
            candidates.append(f"{call.asterisk_channel_id}.WAV")
        if call.asterisk_uniqueid:
            candidates.append(f"{call.asterisk_uniqueid}.wav")
            candidates.append(f"{call.asterisk_uniqueid}.WAV")

        wav_path = None
        for name in candidates:
            path = os.path.join(recordings_path, name)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                wav_path = path
                break

        # Glob fallback: scan the directory for any file whose name contains
        # the channel id — handles hostname-prefixed UNIQUEID variants.
        if not wav_path and call.asterisk_channel_id:
            pattern = os.path.join(recordings_path, f"*{call.asterisk_channel_id}*.wav")
            matches = [p for p in _glob.glob(pattern) if os.path.getsize(p) > 0]
            if matches:
                wav_path = matches[0]

        if not wav_path:
            attempt = self.request.retries + 1
            logger.warning(
                f"Recording not found for call {call_id} "
                f"(attempt {attempt}/5, channel={call.asterisk_channel_id}). "
                f"Retrying in 30 s…"
            )
            raise self.retry(countdown=30)

        logger.info(f"Processing recording: {wav_path}")

        # Convert to MP3 for smaller file size
        mp3_path = wav_path.replace('.wav', '.mp3').replace('.WAV', '.mp3')

        try:
            result = subprocess.run([
                'ffmpeg', '-i', wav_path,
                '-codec:a', 'libmp3lame',
                '-qscale:a', '2',
                '-y',  # Overwrite output file
                mp3_path
            ], check=True, capture_output=True, text=True)

            logger.info(f"Converted recording to MP3: {mp3_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr}")
            # Fall back to using WAV file
            mp3_path = wav_path

        # Get file info
        file_size = os.path.getsize(mp3_path)

        # Create recording record and save file
        with open(mp3_path, 'rb') as f:
            recording = CallRecording.objects.create(
                call=call,
                duration=call.duration,
                file_size=file_size
            )

            filename = f"{call.asterisk_uniqueid or call.id}.mp3"
            recording.file.save(filename, File(f))
            recording.save()

        logger.info(f"Created recording record for call {call_id}")

        # Auto-transcription: only runs if enabled in settings
        from .models import CallTranscript, LANGUAGE_TO_STT_CODE
        from apps.user_settings.models.general import SystemConfiguration

        auto_transcribe = SystemConfiguration.get_setting('transcription_auto_enabled', False)

        # Resolve language: contact preferred → company preferred → system default
        lang_code = ''
        if call.contact_id:
            short = call.contact.effective_language  # 'en' or 'ka'
            lang_code = LANGUAGE_TO_STT_CODE.get(short, '')
        if not lang_code:
            default_lang = SystemConfiguration.get_setting('default_preferred_language', 'en')
            lang_code = LANGUAGE_TO_STT_CODE.get(default_lang, '') or 'en'

        transcript, _ = CallTranscript.objects.get_or_create(call=call)
        transcript.language_code = lang_code
        transcript.save(update_fields=['language_code', 'updated_at'])

        if auto_transcribe:
            task = transcribe_call.delay(call_id)
            transcript.celery_task_id = task.id
            transcript.save(update_fields=['celery_task_id', 'updated_at'])
            logger.info(f"Auto-queued transcription for call {call_id} (lang={lang_code}, task={task.id})")
        else:
            logger.info(f"Recording saved for call {call_id} — auto-transcription disabled")

        # Cleanup temp files; also remove any legacy split files if present
        call_uid = call.asterisk_uniqueid or call.asterisk_channel_id
        try:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            if mp3_path != wav_path and os.path.exists(mp3_path):
                os.remove(mp3_path)
            for suffix in ('-rx.wav', '-tx.wav'):
                split = os.path.join(recordings_path, f"{call_uid}{suffix}")
                if os.path.exists(split):
                    os.remove(split)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")

    except Call.DoesNotExist:
        logger.error(f"Call {call_id} not found")
    except CeleryRetry:
        raise  # propagate retry signal without double-counting
    except Exception as e:
        logger.error(f"Recording processing failed for call {call_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


_LANG_NORMALIZE = {'ka-GE': 'ka', 'en-US': 'en', 'ka': 'ka', 'en': 'en'}


_ELEVENLABS_STT_URL = 'https://api.elevenlabs.io/v1/speech-to-text'


def _build_keywords(call, lang):
    """
    Collect custom_vocabulary keywords for the given language from two sources:
    1. Global default keywords (SystemConfiguration 'stt_keywords_en' / 'stt_keywords_ka')
    2. Team-specific keywords (SalesTeam.stt_keywords_en / stt_keywords_ka)

    Returns a deduplicated list of non-empty strings.
    """
    from apps.user_settings.models.general import SystemConfiguration

    setting_key = f'stt_keywords_{lang}'  # 'stt_keywords_en' or 'stt_keywords_ka'
    team_field = f'stt_keywords_{lang}'    # same naming on SalesTeam

    raw = []

    global_raw = SystemConfiguration.get_setting(setting_key) or ''
    for kw in global_raw.replace(',', '\n').splitlines():
        kw = kw.strip()
        if kw:
            raw.append(kw)

    if call.opportunity_id:
        try:
            team = call.opportunity.sales_team
            if team:
                team_raw = getattr(team, team_field, '') or ''
                for kw in team_raw.replace(',', '\n').splitlines():
                    kw = kw.strip()
                    if kw:
                        raw.append(kw)
        except Exception:
            pass

    # Deduplicate preserving order
    seen = set()
    result = []
    for kw in raw:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            result.append(kw)
    return result


@shared_task(bind=True, max_retries=3)
def transcribe_call(self, call_id):
    """Transcribe call audio using ElevenLabs Scribe STT with speaker diarization."""
    import json
    import requests as http_requests

    from .models import Call, CallTranscript, LANGUAGE_TO_STT_CODE
    from apps.user_settings.models.general import SystemConfiguration

    try:
        call = Call.objects.select_related('contact', 'opportunity__sales_team').get(id=call_id)
    except Call.DoesNotExist:
        logger.error(f"Call {call_id} not found for transcription")
        return

    try:
        transcript = call.transcript
    except CallTranscript.DoesNotExist:
        logger.error(f"No CallTranscript for call {call_id}")
        return

    # Resolve language: contact preferred → stored transcript code → system default → 'en'
    lang = ''
    if call.contact_id:
        raw = call.contact.effective_language  # 'en' or 'ka'
        lang = LANGUAGE_TO_STT_CODE.get(raw, '')
    if not lang and transcript.language_code:
        lang = _LANG_NORMALIZE.get(transcript.language_code, transcript.language_code[:2])
    if not lang:
        default_lang = SystemConfiguration.get_setting('default_preferred_language', 'en')
        lang = LANGUAGE_TO_STT_CODE.get(default_lang, 'en') or 'en'

    # Keep transcript.language_code in sync
    if transcript.language_code != lang:
        transcript.language_code = lang

    api_key = SystemConfiguration.get_setting('elevenlabs_api_key')
    if not api_key:
        transcript.status = CallTranscript.STATUS_FAILED
        transcript.error_message = (
            'ElevenLabs API key is not configured. '
            'Go to Settings → Transcription to add it.'
        )
        transcript.save()
        logger.error(f"ElevenLabs API key not configured — cannot transcribe call {call_id}")
        return

    # Resolve the recording file path
    try:
        recording = call.recording
    except Exception:
        recording = None

    if not recording or not recording.file:
        transcript.status = CallTranscript.STATUS_FAILED
        transcript.error_message = (
            'No recording file found for this call. '
            'Recording may not have been processed yet.'
        )
        transcript.save()
        logger.error(f"No recording for call {call_id} — cannot transcribe")
        return

    audio_path = recording.file.path
    if not os.path.exists(audio_path):
        transcript.status = CallTranscript.STATUS_FAILED
        transcript.error_message = (
            'Recording file not found on disk. '
            'It may have been deleted. A new call recording is required.'
        )
        transcript.save()
        logger.error(f"Recording file missing on disk for call {call_id}: {audio_path}")
        return

    transcript.status = CallTranscript.STATUS_PROCESSING
    transcript.save(update_fields=['status', 'updated_at'])

    headers = {'xi-api-key': api_key}
    keywords = _build_keywords(call, lang)

    form_data = {
        'model_id': 'scribe_v2',
        'language_code': lang,
        'diarize': 'true',
        'num_speakers': '2',
    }
    if keywords:
        form_data['custom_vocabulary'] = json.dumps([{'word': kw} for kw in keywords])
        logger.info(f"Transcribing call {call_id} with {len(keywords)} custom keywords")

    try:
        with open(audio_path, 'rb') as f:
            resp = http_requests.post(
                _ELEVENLABS_STT_URL,
                headers=headers,
                data=form_data,
                files={'file': f},
                timeout=300,
            )
        resp.raise_for_status()
        data = resp.json()

        # Split words by speaker_id: speaker_0 → caller, speaker_1 → agent
        caller_words = []
        agent_words = []
        caller_parts = []
        agent_parts = []

        for w in data.get('words', []):
            if w.get('type', 'word') != 'word':
                continue
            entry = {
                'text': w['text'],
                'start': w.get('start'),
                'end': w.get('end'),
            }
            speaker = w.get('speaker_id', 'speaker_0')
            if speaker == 'speaker_1':
                agent_words.append(entry)
                agent_parts.append(w['text'])
            else:
                caller_words.append(entry)
                caller_parts.append(w['text'])

        transcript.caller_words = caller_words
        transcript.agent_words = agent_words
        transcript.caller_text = ' '.join(caller_parts)
        transcript.agent_text = ' '.join(agent_parts)
        transcript.status = CallTranscript.STATUS_COMPLETED
        transcript.error_message = ''
        transcript.save()
        logger.info(
            f"ElevenLabs transcription completed for call {call_id} "
            f"(caller={len(caller_words)} words, agent={len(agent_words)} words)"
        )

        # Auto-analyze with Claude if enabled
        if SystemConfiguration.get_setting('ai_analysis_auto_enabled', False):
            analyze_call_with_claude.delay(call_id)

    except Exception as e:
        transcript.status = CallTranscript.STATUS_FAILED
        transcript.error_message = str(e)
        transcript.save()
        logger.error(f"ElevenLabs transcription failed for call {call_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def analyze_call_with_claude(self, call_id):
    """
    Analyze a completed call transcript using Claude AI.

    Builds a rich context prompt (product description, keywords, activity types, transcript)
    and asks Claude to suggest follow-up activities and/or direct actions such as sending the
    sales pitch. Each action in the JSON response is executed immediately:
      - "create_activity" → ActivityService.create_activity(...)
      - "send_pitch"      → WhatsAppService.send_sales_pitch(...)
    Results are stored in CallAnalysis for display in the UI.
    """
    import json
    import datetime

    from .models import Call, CallAnalysis, CallTranscript
    from apps.user_settings.models.general import SystemConfiguration
    from apps.activities.models import Activity, ActivityType
    from apps.activities.services.activity_service import ActivityService

    try:
        call = Call.objects.select_related(
            'user', 'contact__company', 'opportunity__sales_team'
        ).get(id=call_id)
    except Call.DoesNotExist:
        logger.error(f"analyze_call_with_claude: call {call_id} not found")
        return

    # Must have a completed transcript
    try:
        transcript = call.transcript
    except CallTranscript.DoesNotExist:
        logger.info(f"analyze_call_with_claude: no transcript for call {call_id}, skipping")
        return

    if transcript.status != CallTranscript.STATUS_COMPLETED:
        logger.info(
            f"analyze_call_with_claude: transcript for call {call_id} not completed "
            f"(status={transcript.status}), skipping"
        )
        return

    if not transcript.caller_text and not transcript.agent_text:
        logger.info(f"analyze_call_with_claude: empty transcript for call {call_id}, skipping")
        return

    # Get/create analysis record
    analysis, created = CallAnalysis.objects.get_or_create(call=call)

    # On re-analysis: delete activities previously created by the last AI run
    if not created and analysis.created_activity_ids:
        prev_activity_ids = [
            item for item in analysis.created_activity_ids
            if isinstance(item, int)
        ]
        if prev_activity_ids:
            deleted_count, _ = Activity.objects.filter(pk__in=prev_activity_ids).delete()
            logger.info(
                f"Re-analysis for call {call_id}: deleted {deleted_count} "
                f"previously AI-created activities {prev_activity_ids}"
            )

    analysis.status = CallAnalysis.STATUS_PROCESSING
    analysis.error_message = ''
    analysis.celery_task_id = self.request.id or ''
    analysis.created_activity_ids = []
    analysis.save(update_fields=['status', 'error_message', 'celery_task_id', 'created_activity_ids', 'updated_at'])

    api_key = SystemConfiguration.get_setting('anthropic_api_key')
    if not api_key:
        analysis.status = CallAnalysis.STATUS_FAILED
        analysis.error_message = (
            'Anthropic API key is not configured. '
            'Go to Settings → Transcription → AI Analysis to add it.'
        )
        analysis.save()
        logger.error(f"Anthropic API key not configured — cannot analyze call {call_id}")
        return

    # Gather context
    activity_types = list(ActivityType.objects.filter(is_active=True).values_list('name', flat=True))
    activity_type_list = '\n'.join(f'- {name}' for name in activity_types) or '- (no activity types defined)'

    product_description = ''
    if call.opportunity_id and call.opportunity.sales_team_id:
        product_description = call.opportunity.sales_team.product_description or ''

    lang = transcript.language_code or 'en'
    if lang not in ('en', 'ka'):
        lang = lang[:2]
    keywords = _build_keywords(call, lang)
    keywords_text = ', '.join(keywords) if keywords else '(none)'

    contact_name = ''
    company_name = ''
    if call.contact_id:
        contact_name = call.contact.name or ''
        if call.contact.company_id:
            company_name = call.contact.company.legal_name or ''
    # Resolve agent user: prefer call.user, fall back to opportunity's assigned_to
    agent_user = call.user
    if not agent_user and call.opportunity_id:
        agent_user = call.opportunity.assigned_to
    agent_name = ''
    if agent_user:
        agent_name = agent_user.get_full_name() or agent_user.username

    call_date = (call.started_at or call.created_at).strftime('%Y-%m-%d %H:%M') if (call.started_at or call.created_at) else ''
    duration_str = call.duration_formatted if call.duration else 'unknown'
    direction_str = call.get_direction_display()
    today = datetime.date.today().isoformat()

    system_prompt = f"""You are a CRM sales assistant. Analyze the sales call and suggest only the essential next actions.

Product / Service being sold:
{product_description or '(not specified)'}

Key topics and terms:
{keywords_text}

Today's date: {today}

Available activity types (use EXACT names for create_activity actions):
{activity_type_list}

Available direct actions:
- "send_pitch" — immediately sends the sales pitch/presentation PDF to the customer via WhatsApp

Rules:
- Suggest AT MOST 2 items total (activities + direct actions combined).
- NEVER create an activity for something that already happened (e.g. the call itself, an "initial contact" that was this call).
- NEVER create duplicate or near-duplicate follow-up activities — one follow-up is enough.
- Only suggest a "create_activity" if there is a clear, concrete next step that must be tracked.
- Only suggest "send_pitch" if the customer explicitly asked to receive materials/presentation.
- If nothing meaningful is needed, return an empty suggested_activities list.

Respond ONLY with valid JSON (no markdown code block, no explanation outside JSON):
{{
  "analysis": "2-3 sentence summary of call outcomes and what the agent should do next",
  "suggested_activities": [
    {{
      "action_type": "create_activity",
      "activity_type_name": "<exact name from the list above>",
      "title": "<concise actionable title>",
      "description": "<context and what needs to be done>",
      "scheduled_date": "<ISO 8601 datetime e.g. 2026-03-01T10:00:00, or null>",
      "notes": "<optional additional notes, or null>"
    }},
    {{
      "action_type": "send_pitch",
      "reason": "<brief reason why pitch should be sent now>"
    }}
  ]
}}"""

    user_prompt = f"""Call Details:
- Date: {call_date}
- Duration: {duration_str}
- Direction: {direction_str}
- Contact: {contact_name or '(unknown)'}{f' from {company_name}' if company_name else ''}
- Sales Agent: {agent_name or '(unknown)'}

--- SALES AGENT ---
{transcript.agent_text or '(no agent transcript)'}

--- CUSTOMER ---
{transcript.caller_text or '(no customer transcript)'}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}],
        )
        raw_response = message.content[0].text.strip()
        logger.info(f"Claude analysis received for call {call_id}: {len(raw_response)} chars")
    except Exception as e:
        analysis.status = CallAnalysis.STATUS_FAILED
        analysis.error_message = f"Anthropic API error: {e}"
        analysis.save()
        logger.error(f"Anthropic API error for call {call_id}: {e}")
        raise self.retry(exc=e, countdown=120)

    # Parse JSON
    try:
        # Strip markdown code fences if Claude wrapped it anyway
        text = raw_response
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            text = text.rsplit('```', 1)[0].strip()
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        analysis.status = CallAnalysis.STATUS_FAILED
        analysis.error_message = f"JSON parse error: {e}. Raw: {raw_response[:500]}"
        analysis.save()
        logger.error(f"JSON parse error for call {call_id}: {e}")
        return

    analysis.analysis_text = data.get('analysis', '')
    analysis.suggested_activities = data.get('suggested_activities', [])
    created_ids = []

    # Execute each suggested action
    for item in analysis.suggested_activities:
        action_type = item.get('action_type', 'create_activity')

        if action_type == 'create_activity':
            if not call.opportunity_id:
                logger.info(f"Skipping create_activity for call {call_id}: no linked opportunity")
                continue
            type_name = item.get('activity_type_name', '').strip()
            try:
                act_type = ActivityType.objects.get(name__iexact=type_name, is_active=True)
            except ActivityType.DoesNotExist:
                logger.warning(
                    f"analyze_call_with_claude: activity type '{type_name}' not found, skipping"
                )
                continue

            scheduled_date_str = item.get('scheduled_date')
            scheduled_date = None
            if scheduled_date_str:
                try:
                    from django.utils.dateparse import parse_datetime
                    scheduled_date = parse_datetime(scheduled_date_str)
                    if scheduled_date is None:
                        from datetime import datetime
                        scheduled_date = datetime.fromisoformat(scheduled_date_str)
                except (ValueError, TypeError):
                    pass

            if scheduled_date is None:
                import datetime as _dt
                from django.utils import timezone as tz
                default_days = int(
                    SystemConfiguration.get_setting('ai_activity_default_days', 1) or 1
                )
                default_date = _dt.date.today() + _dt.timedelta(days=default_days)
                scheduled_date = tz.make_aware(
                    _dt.datetime.combine(default_date, _dt.time(9, 0))
                )

            description = item.get('description', '')
            notes = item.get('notes') or ''
            if notes:
                description = f"{description}\n\n{notes}".strip()

            try:
                from django.utils import timezone
                activity = ActivityService.create_activity(
                    lead_id=call.opportunity_id,
                    activity_type_id=act_type.pk,
                    title=item.get('title', 'Follow-up'),
                    scheduled_date=scheduled_date,
                    created_by=agent_user,
                    assigned_to=agent_user,
                    description=description,
                )
                created_ids.append(activity.pk)
                logger.info(
                    f"Created activity {activity.pk} ('{act_type.name}') for call {call_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to create activity for call {call_id}: {e}")

        elif action_type == 'send_pitch':
            if not call.opportunity_id:
                logger.info(f"Skipping send_pitch for call {call_id}: no linked opportunity")
                continue
            auto_send = SystemConfiguration.get_setting('auto_send_pitch_enabled', False)
            if auto_send:
                try:
                    from apps.messaging.services.whatsapp_service import WhatsAppService
                    wa_msg = WhatsAppService.send_sales_pitch(
                        lead_id=call.opportunity_id,
                        sent_by=agent_user,
                    )
                    # Message accepted by Meta — schedule a delivery status check.
                    # The check task will create a planned activity if delivery fails.
                    check_pitch_delivery.apply_async(
                        kwargs={
                            'wa_message_id': wa_msg.id,
                            'lead_id': call.opportunity_id,
                            'user_id': agent_user.id if agent_user else None,
                            'call_id': call_id,
                        },
                        countdown=30,
                    )
                    created_ids.append({'action': 'send_pitch', 'status': 'sent', 'wa_message_id': wa_msg.id})
                    logger.info(
                        f"Sent sales pitch for call {call_id} (opportunity {call.opportunity_id}), "
                        f"delivery check scheduled for message {wa_msg.id}"
                    )
                except Exception as e:
                    # API-level failure (bad config, missing contact, etc.) — create fallback immediately
                    logger.warning(f"send_pitch API call failed for call {call_id}: {e}")
                    _create_pitch_planned_activity(
                        lead_id=call.opportunity_id,
                        agent_user=agent_user,
                        description=f'Send sales pitch via WhatsApp (auto-send failed: {e})',
                        created_ids=created_ids,
                        call_id=call_id,
                    )
            else:
                # Auto-send disabled — create planned activity directly
                _create_pitch_planned_activity(
                    lead_id=call.opportunity_id,
                    agent_user=agent_user,
                    description='Send sales pitch via WhatsApp',
                    created_ids=created_ids,
                    call_id=call_id,
                )

        else:
            logger.warning(f"Unknown action_type '{action_type}' in Claude response for call {call_id}")

    analysis.created_activity_ids = created_ids
    analysis.status = CallAnalysis.STATUS_COMPLETED
    analysis.save()
    logger.info(
        f"Claude analysis completed for call {call_id}: "
        f"{len(created_ids)} actions executed"
    )


def _create_pitch_planned_activity(*, lead_id, agent_user, description, created_ids, call_id):
    """Create a planned WhatsApp Pitch activity and append its pk to created_ids in-place."""
    try:
        import datetime as _dt
        from django.utils import timezone as tz
        from apps.activities.models import ActivityType
        from apps.activities.services.activity_service import ActivityService

        wa_type = ActivityType.objects.filter(name__icontains='whatsapp').first()
        if not wa_type:
            created_ids.append({'action': 'send_pitch', 'status': 'skipped_no_type'})
            logger.warning(f"No WhatsApp ActivityType found — skipping planned pitch for call {call_id}")
            return
        today = _dt.date.today()
        scheduled = tz.make_aware(_dt.datetime.combine(today, _dt.time(9, 0)))
        activity = ActivityService.create_activity(
            lead_id=lead_id,
            activity_type_id=wa_type.pk,
            title='Send WhatsApp Sales Pitch',
            scheduled_date=scheduled,
            created_by=agent_user,
            assigned_to=agent_user,
            description=description,
        )
        created_ids.append(activity.pk)
        logger.info(f"Created planned WhatsApp Pitch activity {activity.pk} for call {call_id}")
    except Exception as e:
        logger.warning(f"Failed to create planned pitch activity for call {call_id}: {e}")


@shared_task(bind=True, max_retries=2)
def check_pitch_delivery(self, *, wa_message_id, lead_id, user_id, call_id):
    """
    Check whether a WhatsApp sales pitch message was actually delivered.
    Runs ~30 s after sending. Retries up to 2× (30 s apart) if status is still 'sent'.
    Creates a planned activity on the lead if delivery fails or remains unknown.
    Also appends the activity pk to CallAnalysis.created_activity_ids so re-analysis
    cleanup works correctly.
    """
    from apps.messaging.models import WhatsAppMessage

    try:
        msg = WhatsAppMessage.objects.get(id=wa_message_id)
    except WhatsAppMessage.DoesNotExist:
        logger.warning(f"check_pitch_delivery: message {wa_message_id} not found")
        return

    if msg.status in ('delivered', 'read'):
        logger.info(f"Pitch message {wa_message_id} delivered successfully — no action needed")
        return

    if msg.status == 'sent':
        # Webhook hasn't arrived yet — retry
        if self.request.retries < self.max_retries:
            logger.info(f"Pitch message {wa_message_id} still 'sent', retrying delivery check")
            raise self.retry(countdown=30)
        # Max retries exhausted — treat as unknown
        note = 'delivery status unknown after 90 s — verify manually'
        logger.warning(f"Pitch message {wa_message_id} status unknown after retries")
    else:
        # status == 'failed'
        note = 'automatic send failed to deliver'
        logger.warning(f"Pitch message {wa_message_id} delivery failed")

    # Resolve agent user
    from core.models import User
    agent_user = User.objects.filter(id=user_id).first() if user_id else None

    # Create the planned fallback activity
    created_ids = []
    _create_pitch_planned_activity(
        lead_id=lead_id,
        agent_user=agent_user,
        description=f'Send sales pitch via WhatsApp ({note})',
        created_ids=created_ids,
        call_id=call_id,
    )

    # Append the new activity pk to CallAnalysis so re-analysis cleanup can find it
    if created_ids:
        try:
            from .models import CallAnalysis, Call
            analysis = CallAnalysis.objects.get(call_id=call_id)
            ids = list(analysis.created_activity_ids or [])
            ids.extend(created_ids)
            analysis.created_activity_ids = ids
            analysis.save(update_fields=['created_activity_ids', 'updated_at'])
        except Exception as e:
            logger.warning(f"check_pitch_delivery: could not update CallAnalysis for call {call_id}: {e}")


@shared_task
def cleanup_old_recordings(days=90):
    """
    Clean up recordings older than specified days.

    This helps manage storage by removing old recordings that are no longer needed.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import CallRecording

    cutoff_date = timezone.now() - timedelta(days=days)

    old_recordings = CallRecording.objects.filter(created_at__lt=cutoff_date)
    count = old_recordings.count()

    for recording in old_recordings:
        # Delete the file
        if recording.file:
            recording.file.delete(save=False)
        recording.delete()

    logger.info(f"Cleaned up {count} recordings older than {days} days")
    return count


@shared_task
def sync_asterisk_recordings():
    """
    Sync any recordings from Asterisk that weren't processed in real-time.

    This catches any recordings that may have been missed due to
    service downtime or processing errors.
    """
    from .models import Call, CallRecording
    from django.utils import timezone
    from datetime import timedelta

    recordings_path = getattr(
        settings,
        'ASTERISK_RECORDINGS_PATH',
        '/var/spool/asterisk/monitor'
    )

    if not os.path.exists(recordings_path):
        logger.warning(f"Recordings path does not exist: {recordings_path}")
        return

    # Get calls from last 24 hours that don't have recordings
    cutoff = timezone.now() - timedelta(hours=24)
    calls_without_recordings = Call.objects.filter(
        created_at__gte=cutoff,
        status='ended',
        recording__isnull=True
    )

    processed = 0
    for call in calls_without_recordings:
        try:
            process_recording.delay(call.id)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to sync recording for call {call.id}: {e}")

    logger.info(f"Synced {processed} recordings")
    return processed


@shared_task
def update_call_statistics():
    """
    Update call statistics for reporting.

    This task aggregates call data for dashboards and reports.
    """
    from django.db.models import Count, Sum, Avg, Q
    from django.core.cache import cache
    from django.utils import timezone
    from .models import Call
    from datetime import timedelta

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Today's stats
    today_stats = Call.objects.filter(
        created_at__date=today
    ).aggregate(
        total=Count('id'),
        answered=Count('id', filter=Q(status='answered')),
        total_duration=Sum('duration'),
        avg_duration=Avg('duration'),
    )

    # Weekly stats
    weekly_stats = Call.objects.filter(
        created_at__date__gte=week_ago
    ).aggregate(
        total=Count('id'),
        answered=Count('id', filter=Q(status='answered')),
        total_duration=Sum('duration'),
        avg_duration=Avg('duration'),
    )

    # Monthly stats
    monthly_stats = Call.objects.filter(
        created_at__date__gte=month_ago
    ).aggregate(
        total=Count('id'),
        answered=Count('id', filter=Q(status='answered')),
        total_duration=Sum('duration'),
        avg_duration=Avg('duration'),
    )

    # Cache the stats
    cache.set('call_stats_today', today_stats, 300)  # 5 minutes
    cache.set('call_stats_weekly', weekly_stats, 300)
    cache.set('call_stats_monthly', monthly_stats, 300)

    logger.info("Updated call statistics")
    return {
        'today': today_stats,
        'weekly': weekly_stats,
        'monthly': monthly_stats,
    }
