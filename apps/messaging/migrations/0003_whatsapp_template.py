from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0002_whatsapp_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppTemplate",
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
                (
                    "name",
                    models.CharField(
                        help_text="Exact template name as registered in Meta (e.g. hello_world)",
                        max_length=200,
                        unique=True,
                    ),
                ),
                (
                    "display_name",
                    models.CharField(
                        help_text="Friendly label shown to agents",
                        max_length=200,
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        default="en_US",
                        help_text="BCP-47 language code (e.g. en_US, ar, pt_BR)",
                        max_length=20,
                    ),
                ),
                (
                    "body_preview",
                    models.TextField(
                        help_text="Body text with {{1}}, {{2}} placeholders",
                    ),
                ),
                (
                    "variable_names",
                    models.JSONField(
                        default=list,
                        help_text="Ordered list of UI labels for each placeholder (e.g. ['Customer Name', 'Date'])",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "WhatsApp Template",
                "verbose_name_plural": "WhatsApp Templates",
                "ordering": ["display_name"],
                "app_label": "messaging",
            },
        ),
    ]
