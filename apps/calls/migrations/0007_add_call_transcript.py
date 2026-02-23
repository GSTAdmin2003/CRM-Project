from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0006_call_activity_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallTranscript',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('processing', 'Processing'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('language_code', models.CharField(
                    blank=True,
                    help_text='BCP-47 code, e.g. en-US or ka-GE. Blank = awaiting user selection.',
                    max_length=10,
                )),
                ('caller_text', models.TextField(blank=True, help_text='Transcription of the caller channel (rx).')),
                ('agent_text', models.TextField(blank=True, help_text='Transcription of the agent channel (tx).')),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('call', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transcript',
                    to='calls.call',
                )),
            ],
            options={
                'verbose_name': 'Call Transcript',
                'verbose_name_plural': 'Call Transcripts',
            },
        ),
    ]
