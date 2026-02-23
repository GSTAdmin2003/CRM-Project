from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0010_salesteam_stt_keywords"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="salesteam",
            name="stt_keywords",
        ),
        migrations.AddField(
            model_name="salesteam",
            name="stt_keywords_en",
            field=models.TextField(
                blank=True,
                verbose_name="STT Keywords (English)",
                help_text="English keywords passed to ElevenLabs for calls linked to this team. One per line or comma-separated.",
            ),
        ),
        migrations.AddField(
            model_name="salesteam",
            name="stt_keywords_ka",
            field=models.TextField(
                blank=True,
                verbose_name="STT Keywords (Georgian)",
                help_text="Georgian keywords passed to ElevenLabs for calls linked to this team. One per line or comma-separated.",
            ),
        ),
    ]
