from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calls", "0004_add_hold_music"),
    ]

    operations = [
        migrations.AddField(
            model_name="sipsettings",
            name="welcome_sound",
            field=models.FileField(
                blank=True,
                help_text="Audio greeting played to callers before ringing the agent (mp3 or wav)",
                null=True,
                upload_to="custom_sounds/",
                verbose_name="Welcome Sound",
            ),
        ),
        migrations.AddField(
            model_name="sipsettings",
            name="non_working_hours_sound",
            field=models.FileField(
                blank=True,
                help_text="Audio message played outside business hours (mp3 or wav)",
                null=True,
                upload_to="custom_sounds/",
                verbose_name="Non-Working Hours Sound",
            ),
        ),
        migrations.AddField(
            model_name="sipsettings",
            name="working_hours_start",
            field=models.TimeField(
                blank=True,
                help_text="e.g. 09:00",
                null=True,
                verbose_name="Working Hours Start",
            ),
        ),
        migrations.AddField(
            model_name="sipsettings",
            name="working_hours_end",
            field=models.TimeField(
                blank=True,
                help_text="e.g. 17:00",
                null=True,
                verbose_name="Working Hours End",
            ),
        ),
        migrations.AddField(
            model_name="sipsettings",
            name="working_days",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Comma-separated Asterisk day names, e.g. mon,tue,wed,thu,fri",
                max_length=100,
                verbose_name="Working Days",
            ),
        ),
    ]
