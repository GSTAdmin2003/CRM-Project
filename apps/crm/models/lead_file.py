from django.db import models

from core.models import User


class LeadFile(models.Model):
    """File attachments for opportunities"""

    lead = models.ForeignKey("crm.Lead", on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="leads/files/")
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.lead.title} - {self.filename}"
