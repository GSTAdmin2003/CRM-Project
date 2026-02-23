from django.db import migrations


def rename_ka_template(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="sales_pitch", language="ka").update(name="sales_pitch_ka")


def reverse_rename_ka_template(apps, schema_editor):
    M = apps.get_model("messaging", "WhatsAppTemplate")
    M.objects.filter(name="sales_pitch_ka", language="ka").update(name="sales_pitch")


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0005_add_app_id_to_whatsapp_config"),
    ]

    operations = [
        migrations.RunPython(rename_ka_template, reverse_rename_ka_template),
    ]
