import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _migrate_existing_calls(apps, schema_editor):
    """
    For every existing Call that is linked to an Activity, create a
    PhoneCallExtension so the activity has its extension populated.
    """
    Call = apps.get_model("calls", "Call")
    PhoneCallExtension = apps.get_model("activities", "PhoneCallExtension")

    for call in Call.objects.filter(activity_id__isnull=False).select_related("activity"):
        # Guard against duplicate (e.g. two calls linked to same activity)
        if PhoneCallExtension.objects.filter(activity_id=call.activity_id).exists():
            continue
        PhoneCallExtension.objects.create(
            activity_id=call.activity_id,
            ari_call_id=call.id,
            direction=call.direction or "",
            call_status=call.status or "initiated",
            from_number=call.from_number or "",
            to_number=call.to_number or "",
            asterisk_channel_id=call.asterisk_channel_id or "",
            asterisk_uniqueid=call.asterisk_uniqueid or "",
            contact_id=call.contact_id,
            user_id=call.user_id,
            duration=call.duration,
            started_at=call.started_at,
            answered_at=call.answered_at,
            ended_at=call.ended_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0004_unify_lead_incominglead"),
        ("calls", "0011_calltranscript_celery_task_id"),
        ("contacts", "0003_add_preferred_language"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PhoneCallExtension",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "activity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phone_call",
                        to="activities.activity",
                    ),
                ),
                (
                    "ari_call",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="extension",
                        to="calls.call",
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        blank=True,
                        choices=[("inbound", "Inbound"), ("outbound", "Outbound")],
                        max_length=10,
                    ),
                ),
                (
                    "call_status",
                    models.CharField(
                        choices=[
                            ("initiated", "Initiated"),
                            ("ringing", "Ringing"),
                            ("answered", "Answered"),
                            ("ended", "Ended"),
                            ("failed", "Failed"),
                            ("busy", "Busy"),
                            ("no_answer", "No Answer"),
                        ],
                        default="initiated",
                        max_length=20,
                    ),
                ),
                ("from_number", models.CharField(blank=True, max_length=20)),
                ("to_number", models.CharField(blank=True, max_length=20)),
                (
                    "asterisk_channel_id",
                    models.CharField(blank=True, db_index=True, max_length=128),
                ),
                ("asterisk_uniqueid", models.CharField(blank=True, max_length=64)),
                (
                    "contact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="phone_call_activities",
                        to="contacts.contact",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="phone_call_activities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "duration",
                    models.PositiveIntegerField(
                        blank=True, help_text="Duration in seconds", null=True
                    ),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("answered_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Phone Call Extension",
                "verbose_name_plural": "Phone Call Extensions",
                "app_label": "activities",
            },
        ),
        migrations.RunPython(
            code=_migrate_existing_calls,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
