from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0010_remove_transcript_correction'),
    ]

    operations = [
        migrations.AddField(
            model_name='calltranscript',
            name='celery_task_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
