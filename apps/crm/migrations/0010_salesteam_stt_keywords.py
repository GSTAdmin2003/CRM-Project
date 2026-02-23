from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0009_salesteam_ka_pitch"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesteam",
            name="stt_keywords",
            field=models.TextField(
                blank=True,
                help_text="Keywords for this team passed to ElevenLabs during transcription. "
                          "One per line or comma-separated.",
            ),
        ),
    ]
