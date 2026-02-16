"""
Signals for the calls app
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Call, SIPSettings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Call)
def call_saved(sender, instance, created, **kwargs):
    """Handle call save events"""
    if created:
        # Log call creation if needed
        pass


@receiver(post_save, sender=SIPSettings)
def sip_settings_saved(sender, instance, **kwargs):
    """
    When SIP credentials are saved, generate the Asterisk PJSIP trunk
    config and reload the module so that `sip-trunk-endpoint` exists.
    """
    from .asterisk_config import apply_sip_settings

    logger.info(f"SIP settings saved for user {instance.user_id}, applying to Asterisk...")
    try:
        apply_sip_settings(instance)
    except Exception as e:
        logger.error(f"Failed to apply SIP settings to Asterisk: {e}")


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
