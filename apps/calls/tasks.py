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
except ImportError:
    # Celery not installed - create a dummy decorator
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


@shared_task(bind=True, max_retries=3)
def process_recording(self, call_id):
    """
    Process and import recording from Asterisk.

    This task:
    1. Locates the WAV recording in Asterisk's recording directory
    2. Converts it to MP3 for smaller file size
    3. Creates a CallRecording record with the file
    4. Cleans up temporary files
    """
    from .models import Call, CallRecording

    try:
        call = Call.objects.get(id=call_id)

        # Check if recording already exists
        if hasattr(call, 'recording') and call.recording:
            logger.info(f"Recording already exists for call {call_id}")
            return

        # Recording path in Asterisk
        recordings_path = getattr(
            settings,
            'ASTERISK_RECORDINGS_PATH',
            '/var/spool/asterisk/monitor'
        )

        # Try to find the recording file
        # Asterisk names recordings with the unique ID
        recording_patterns = [
            f"{call.asterisk_uniqueid}.wav",
            f"{call.asterisk_channel_id}.wav",
            f"{call.asterisk_uniqueid}.WAV",
        ]

        wav_path = None
        for pattern in recording_patterns:
            potential_path = os.path.join(recordings_path, pattern)
            if os.path.exists(potential_path):
                wav_path = potential_path
                break

        if not wav_path:
            logger.warning(f"No recording found for call {call_id}")
            return

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

    except Exception as e:
        transcript.status = CallTranscript.STATUS_FAILED
        transcript.error_message = str(e)
        transcript.save()
        logger.error(f"ElevenLabs transcription failed for call {call_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


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
            process_recording(call.id)
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
