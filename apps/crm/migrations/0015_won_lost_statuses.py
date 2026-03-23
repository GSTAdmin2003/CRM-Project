from django.db import migrations, models


def migrate_won_lost_to_statuses(apps, schema_editor):
    Lead = apps.get_model("crm", "Lead")
    LeadStage = apps.get_model("crm", "LeadStage")

    won_stage_ids = list(LeadStage.objects.filter(stage_type="won").values_list("id", flat=True))
    if won_stage_ids:
        Lead.objects.filter(stage_id__in=won_stage_ids).update(status="won", stage=None)

    lost_stage_ids = list(LeadStage.objects.filter(stage_type="lost").values_list("id", flat=True))
    if lost_stage_ids:
        Lead.objects.filter(stage_id__in=lost_stage_ids).update(status="lost", stage=None)

    Lead.objects.filter(status="rejected").update(status="lost")

    LeadStage.objects.filter(stage_type__in=["won", "lost"]).update(is_active=False, stage_type="normal")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0014_leadstage_stage_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lead",
            name="status",
            field=models.CharField(
                max_length=20,
                choices=[("new", "New"),("converted", "Converted"),("won", "Won"),("lost", "Lost")],
                default="new",
            ),
        ),
        migrations.RunPython(migrate_won_lost_to_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="leadstage",
            name="stage_type",
            field=models.CharField(
                max_length=10,
                choices=[("normal", "Normal"),("contacted", "Contacted")],
                default="normal",
            ),
        ),
    ]
