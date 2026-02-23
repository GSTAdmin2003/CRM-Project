from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0009_transcript_correction'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TranscriptCorrection',
        ),
    ]
