"""
Signals for the calls app
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Call


@receiver(post_save, sender=Call)
def call_saved(sender, instance, created, **kwargs):
    """Handle call save events"""
    if created:
        # Log call creation if needed
        pass
