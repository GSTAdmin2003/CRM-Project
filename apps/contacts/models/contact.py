from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .company import Company


LANGUAGE_CHOICES = [('en', 'English'), ('ka', 'Georgian')]


class Contact(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=200, verbose_name="Full Name")
    position = models.CharField(max_length=100, verbose_name="Position")
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    preferred_language = models.CharField(
        max_length=10, choices=LANGUAGE_CHOICES, default='en', blank=True,
        verbose_name="Preferred Language"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'contacts'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.position} at {self.company.display_name}"

    def save(self, *args, **kwargs):
        from core.utils import normalize_phone
        self.phone = normalize_phone(self.phone)
        self.mobile = normalize_phone(self.mobile)
        super().save(*args, **kwargs)

    @property
    def effective_language(self):
        return self.preferred_language or 'en'


@receiver(post_save, sender=Contact)
def set_favorite_contact_on_create(sender, instance, created, **kwargs):
    """Automatically set the first contact as favorite when a new contact is created for a company."""
    if created and not instance.company.favorite_contact:
        instance.company.favorite_contact = instance
        instance.company.save(update_fields=['favorite_contact'])
