"""
Signals for the calls app
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Call, SIPSettings

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"ended", "failed", "busy", "no_answer"}

_OUTCOME_MAP = {
    "failed": "Call failed — could not connect",
    "busy": "Call attempt — line was busy",
    "no_answer": "Call attempt — no answer",
    "ended": "Call ended without connection",
}


@receiver(post_save, sender=Call)
def call_saved(sender, instance, created, **kwargs):
    """Handle call save events"""
    if created:
        # Log call creation if needed
        pass


@receiver(post_save, sender=Call)
def handle_call_ended_activity(sender, instance, **kwargs):
    """Auto-complete linked activity when call ends without being answered."""
    if not instance.activity_id:
        return
    if instance.status not in _TERMINAL_STATUSES:
        return
    if instance.answered_at:
        return  # Answered — user completes via feedback modal

    from apps.activities.models import Activity

    Activity.objects.filter(pk=instance.activity_id, status="planned").update(
        status="completed",
        outcome=_OUTCOME_MAP.get(instance.status, f"Call {instance.status}"),
        completed_at=timezone.now(),
    )


@receiver(post_save, sender=SIPSettings)
def sip_settings_saved(sender, instance, **kwargs):
    """
    When SIP credentials are saved, write the trunk config file.
    We only write the file here — the PJSIP module reload is handled
    by the view when trunk credentials actually change. Reloading
    res_pjsip.so drops the trunk registration and breaks inbound calls.
    """
    from .asterisk_config import write_trunk_config

    logger.info(f"SIP settings saved for user {instance.user_id}, writing trunk config...")
    try:
        write_trunk_config(instance)
    except Exception as e:
        logger.error(f"Failed to write trunk config: {e}")


@receiver(post_delete, sender=SIPSettings)
def sip_settings_deleted(sender, instance, **kwargs):
    """
    When SIP credentials are deleted, write an empty config and
    reload Asterisk to remove the trunk endpoint.
    """
    from .asterisk_config import apply_sip_settings

    logger.info(f"SIP settings deleted for user {instance.user_id}, clearing Asterisk config...")
    try:
        apply_sip_settings(None)
    except Exception as e:
        logger.error(f"Failed to clear Asterisk config: {e}")
