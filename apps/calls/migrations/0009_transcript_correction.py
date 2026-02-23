from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0008_calltranscript_words'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TranscriptCorrection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wrong_text', models.CharField(
                    blank=True, max_length=200,
                    help_text='Text ElevenLabs incorrectly transcribes. Leave blank to whitelist correct_text only.',
                )),
                ('correct_text', models.CharField(
                    max_length=200,
                    help_text='Correct word/phrase, or a domain word to always keep.',
                )),
                ('language', models.CharField(
                    choices=[('ka', 'Georgian'), ('en', 'English'), ('*', 'All languages')],
                    default='*', max_length=5,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Transcript Correction',
                'verbose_name_plural': 'Transcript Corrections',
                'ordering': ['language', 'correct_text'],
            },
        ),
    ]
