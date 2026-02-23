from django.db import models
from core.models import User


class SalesTeam(models.Model):
    """Sales team model for organizing users"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_teams"
    )
    is_active = models.BooleanField(default=True)
    pitch_pdf = models.FileField(upload_to='pitch_pdfs/', blank=True, verbose_name='Pitch PDF (English)')
    pitch_pdf_media_id = models.CharField(max_length=200, blank=True, verbose_name='Pitch PDF Media ID (English)')
    pitch_pdf_filename = models.CharField(max_length=200, blank=True, verbose_name='Pitch PDF Filename (English)')
    pitch_pdf_ka = models.FileField(upload_to='pitch_pdfs/', blank=True, verbose_name='Pitch PDF (Georgian)')
    pitch_pdf_media_id_ka = models.CharField(max_length=200, blank=True, verbose_name='Pitch PDF Media ID (Georgian)')
    pitch_pdf_filename_ka = models.CharField(max_length=200, blank=True, verbose_name='Pitch PDF Filename (Georgian)')
    product_description = models.TextField(
        blank=True,
        verbose_name='Product Description',
        help_text='Description of the product or service this team sells.',
    )
    stt_keywords_en = models.TextField(
        blank=True,
        verbose_name='STT Keywords (English)',
        help_text='English keywords passed to ElevenLabs for calls linked to this team. '
                  'One per line or comma-separated.',
    )
    stt_keywords_ka = models.TextField(
        blank=True,
        verbose_name='STT Keywords (Georgian)',
        help_text='Georgian keywords passed to ElevenLabs for calls linked to this team. '
                  'One per line or comma-separated.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_team_members(self):
        """Get all active team members"""
        return User.objects.filter(sales_team=self, is_active=True)

    def get_pitch_for_language(self, lang: str) -> tuple:
        """Return (media_id, filename) for the given language, falling back to English."""
        if lang == 'ka' and self.pitch_pdf_media_id_ka:
            return self.pitch_pdf_media_id_ka, self.pitch_pdf_filename_ka or 'sales_pitch.pdf'
        return self.pitch_pdf_media_id, self.pitch_pdf_filename or 'sales_pitch.pdf'

    def get_team_leads(self):
        """Get all leads assigned to team members"""
        from apps.crm.models.lead import Lead

        team_members = self.get_team_members()
        return Lead.objects.filter(assigned_to__in=team_members)
