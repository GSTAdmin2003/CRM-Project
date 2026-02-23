from django.db import migrations


def rename_en_template(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="sales_pitch", language="en").update(name="sales_pitch_en")


def reverse_rename_en_template(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="sales_pitch_en", language="en").update(name="sales_pitch")


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0006_rename_ka_template"),
    ]

    operations = [
        migrations.RunPython(rename_en_template, reverse_rename_en_template),
    ]
