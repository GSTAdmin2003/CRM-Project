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

        # Cleanup temporary files
        try:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            if mp3_path != wav_path and os.path.exists(mp3_path):
                os.remove(mp3_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")

    except Call.DoesNotExist:
        logger.error(f"Call {call_id} not found")
    except Exception as e:
        logger.error(f"Recording processing failed for call {call_id}: {e}")
        # Retry with exponential backoff
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
