from django.db import migrations


def rename_ka(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="hello_how_are_you", language="ka").update(
        name="hello_how_are_you_ka"
    )


def reverse_rename_ka(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="hello_how_are_you_ka", language="ka").update(
        name="hello_how_are_you"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0010_seed_greeting_template"),
    ]

    operations = [
        migrations.RunPython(rename_ka, reverse_rename_ka),
    ]
