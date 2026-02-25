from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("calls", "0011_calltranscript_celery_task_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("call", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="analysis", to="calls.call")),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("processing", "Processing"),
                        ("completed", "Completed"),
                        ("failed", "Failed"),
                    ],
                    default="pending",
                    max_length=20,
                )),
                ("analysis_text", models.TextField(blank=True, help_text="Claude's 2-3 sentence call summary.")),
                ("suggested_activities", models.JSONField(
                    blank=True,
                    default=list,
                    help_text="Raw action array from Claude (create_activity / send_pitch commands).",
                )),
                ("created_activity_ids", models.JSONField(
                    blank=True,
                    default=list,
                    help_text="PKs of Activity objects created, or action-result dicts for direct actions.",
                )),
                ("error_message", models.TextField(blank=True)),
                ("celery_task_id", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Call Analysis",
                "verbose_name_plural": "Call Analyses",
            },
        ),
    ]
