from django.db import migrations


def seed(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.get_or_create(
        name="hello_how_are_you",
        language="en",
        defaults={
            "display_name": "Greeting (English)",
            "body_preview": "Hello, How are you?",
            "variable_names": [],
            "is_active": True,
            "approval_status": "draft",
        },
    )
    M.objects.get_or_create(
        name="hello_how_are_you",
        language="ka",
        defaults={
            "display_name": "Greeting (Georgian)",
            "body_preview": "გამარჯობა, როგორ ბრძანდებით?",
            "variable_names": [],
            "is_active": True,
            "approval_status": "draft",
        },
    )


def unseed(apps, schema_editor):
    apps.get_model("messaging", "WhatsAppTemplate").objects.filter(
        name="hello_how_are_you"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0009_meta_error_fields"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
