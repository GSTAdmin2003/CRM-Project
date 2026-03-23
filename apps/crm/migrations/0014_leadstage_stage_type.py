from django.db import migrations, models


def set_stage_types(apps, schema_editor):
    LeadStage = apps.get_model("crm", "LeadStage")
    LeadStage.objects.filter(name__iexact="contacted").update(stage_type="contacted")
    LeadStage.objects.filter(name__iexact="won").update(stage_type="won")
    LeadStage.objects.filter(name__iexact="lost").update(stage_type="lost")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0013_lead_status_discriminator"),
    ]

    operations = [
        migrations.AddField(
            model_name="leadstage",
            name="stage_type",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("normal", "Normal"),
                    ("contacted", "Contacted"),
                    ("won", "Won"),
                    ("lost", "Lost"),
                ],
                default="normal",
            ),
        ),
        migrations.RunPython(set_stage_types, migrations.RunPython.noop),
    ]
