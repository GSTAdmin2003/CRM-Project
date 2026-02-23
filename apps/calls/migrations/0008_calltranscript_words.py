from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0007_add_call_transcript'),
    ]

    operations = [
        migrations.AddField(
            model_name='calltranscript',
            name='caller_words',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"text": "word", "start": 0.5, "end": 0.8}, ...]',
            ),
        ),
        migrations.AddField(
            model_name='calltranscript',
            name='agent_words',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"text": "word", "start": 0.5, "end": 0.8}, ...]',
            ),
        ),
    ]
