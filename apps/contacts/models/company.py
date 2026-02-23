from django.db import models
from django.urls import reverse
from core.models import User


class Company(models.Model):
    CONTACT_TYPE_COMPANY = 'company'
    CONTACT_TYPE_INDIVIDUAL = 'individual'
    CONTACT_TYPE_CHOICES = [
        (CONTACT_TYPE_COMPANY, 'Company'),
        (CONTACT_TYPE_INDIVIDUAL, 'Individual'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ka', 'Georgian'),
    ]
    _LANG_NAMES = {'en': 'English', 'ka': 'Georgian'}

    contact_type = models.CharField(
        max_length=20,
        choices=CONTACT_TYPE_CHOICES,
        default=CONTACT_TYPE_COMPANY,
        verbose_name="Contact Type",
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        blank=True,
        default='',
        verbose_name="Preferred Language",
    )
    legal_id = models.CharField(max_length=100, unique=True, verbose_name="Legal ID")
    legal_name = models.CharField(max_length=200, verbose_name="Legal Name")
    brand_name = models.CharField(max_length=200, blank=True, verbose_name="Brand Name")
    company_phone = models.CharField(max_length=20, blank=True, verbose_name="Company Phone")
    company_mobile = models.CharField(max_length=20, blank=True, verbose_name="Company Mobile")
    company_email = models.EmailField(blank=True, verbose_name="Company Email")
    industry = models.CharField(max_length=100, blank=True, verbose_name="Industry")
    category = models.CharField(max_length=100, blank=True, verbose_name="Category")
    favorite_contact = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='favorited_by_companies', verbose_name="Favorite Contact")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_companies')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_companies')

    class Meta:
        app_label = 'contacts'
        verbose_name_plural = "Companies"
        ordering = ['legal_name']

    def __str__(self):
        return f"{self.legal_name} ({self.legal_id})"

    def get_absolute_url(self):
        return reverse('contacts:company_detail', kwargs={'pk': self.pk})

    @property
    def display_name(self):
        return self.brand_name if self.brand_name else self.legal_name

    @property
    def effective_preferred_language(self) -> str:
        """Resolve actual language: explicit setting → system default."""
        if self.preferred_language:
            return self.preferred_language
        from apps.user_settings.models import SystemConfiguration
        return SystemConfiguration.get_setting('default_preferred_language', 'en')

    @property
    def preferred_language_display(self) -> str:
        """Human-readable language with fallback source noted."""
        if self.preferred_language:
            return self._LANG_NAMES.get(self.preferred_language, self.preferred_language)
        from apps.user_settings.models import SystemConfiguration
        lang = SystemConfiguration.get_setting('default_preferred_language', 'en')
        return f"{self._LANG_NAMES.get(lang, lang)} (System Default)"

    def set_default_favorite_contact(self):
        """Set the first contact as favorite if no favorite is set and contacts exist."""
        if not self.favorite_contact and self.contacts.exists():
            self.favorite_contact = self.contacts.first()
            self.save()

    def ensure_favorite_contact(self):
        """Ensure that if contacts exist, one of them is marked as favorite."""
        if self.contacts.exists():
            if not self.favorite_contact or self.favorite_contact not in self.contacts.all():
                self.favorite_contact = self.contacts.first()
                self.save()
        else:
            # No contacts exist, clear favorite
            if self.favorite_contact:
                self.favorite_contact = None
                self.save()

    def save(self, *args, **kwargs):
        from core.utils import normalize_phone
        self.company_phone = normalize_phone(self.company_phone)
        self.company_mobile = normalize_phone(self.company_mobile)
        super().save(*args, **kwargs)
        # Auto-set favorite contact if none exists and we have contacts
        if not self.favorite_contact and self.contacts.exists():
            self.favorite_contact = self.contacts.first()
            super().save(update_fields=['favorite_contact'])
