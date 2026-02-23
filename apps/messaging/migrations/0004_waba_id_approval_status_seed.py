from django.db import migrations, models


def seed_sales_pitch_templates(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.get_or_create(
        name="sales_pitch",
        language="en",
        defaults={
            "display_name": "Sales Pitch (English)",
            "body_preview": "Hello {{1}}, please find our sales proposal attached.",
            "variable_names": ["Contact Name"],
            "is_active": True,
            "approval_status": "draft",
        },
    )
    M.objects.get_or_create(
        name="sales_pitch",
        language="ka",
        defaults={
            "display_name": "Sales Pitch (Georgian)",
            "body_preview": "გამარჯობა {{1}}, გთხოვთ გაეცნოთ ჩვენს გაყიდვების წინადადებას.",
            "variable_names": ["Contact Name"],
            "is_active": True,
            "approval_status": "draft",
        },
    )


def unseed_sales_pitch_templates(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="sales_pitch").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0003_whatsapp_template"),
    ]

    operations = [
        # 1. Add waba_id to WhatsAppConfig
        migrations.AddField(
            model_name="whatsappconfig",
            name="waba_id",
            field=models.CharField(
                blank=True,
                help_text="WhatsApp Business Account ID (required for template submission)",
                max_length=100,
            ),
        ),
        # 2. Remove unique=True from WhatsAppTemplate.name
        migrations.AlterField(
            model_name="whatsapptemplate",
            name="name",
            field=models.CharField(
                help_text="Exact template name as registered in Meta (e.g. hello_world)",
                max_length=200,
            ),
        ),
        # 3. Add unique_together(name, language) constraint
        migrations.AddConstraint(
            model_name="whatsapptemplate",
            constraint=models.UniqueConstraint(
                fields=["name", "language"], name="unique_template_name_language"
            ),
        ),
        # 4. Add approval_status field
        migrations.AddField(
            model_name="whatsapptemplate",
            name="approval_status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending", "Pending Approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("paused", "Paused"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        # 5. Seed the two fixed sales_pitch templates
        migrations.RunPython(
            seed_sales_pitch_templates,
            unseed_sales_pitch_templates,
        ),
    ]
