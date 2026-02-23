from django.db import migrations, models


def add_app_registry_entry(apps, schema_editor):
    AppRegistry = apps.get_model("core", "AppRegistry")
    AppRegistry.objects.get_or_create(
        name="messaging",
        defaults={
            "display_name": "WhatsApp",
            "description": "Two-way WhatsApp messaging via Meta Cloud API",
            "url_name": "messaging:inbox",
            "is_active": True,
            "order": 15,
        },
    )


def remove_app_registry_entry(apps, schema_editor):
    AppRegistry = apps.get_model("core", "AppRegistry")
    AppRegistry.objects.filter(name="messaging").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0001_initial"),
        ("core", "0005_fix_settings_app_url_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("access_token", models.TextField(blank=True, help_text="Permanent access token from Meta Business Suite")),
                ("phone_number_id", models.CharField(blank=True, max_length=100, help_text="Phone Number ID from Meta developer console")),
                ("app_secret", models.CharField(blank=True, max_length=300, help_text="App Secret used to verify webhook signatures")),
                ("webhook_verify_token", models.CharField(default="crm-webhook-token", max_length=200, help_text="Token you set in Meta webhook configuration")),
                ("is_active", models.BooleanField(default=False, help_text="Enable/disable WhatsApp integration")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "WhatsApp Configuration",
                "app_label": "messaging",
            },
        ),
        migrations.RunPython(add_app_registry_entry, remove_app_registry_entry),
    ]
