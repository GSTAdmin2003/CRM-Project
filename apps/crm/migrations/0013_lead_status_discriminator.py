from django.db import migrations, models


def migrate_status(apps, schema_editor):
    """Set status='converted' on all opportunity records that aren't already rejected."""
    Lead = apps.get_model("crm", "Lead")
    Lead.objects.filter(lead_type="opportunity").exclude(status="rejected").update(
        status="converted"
    )
    # Lead records keep their existing status (new/converted/rejected already correct)


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0012_salesteam_product_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="lead",
            name="lost_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(migrate_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="lead",
            name="lead_type",
        ),
        migrations.AlterField(
            model_name="lead",
            name="status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("new", "New"),
                    ("converted", "Converted"),
                    ("rejected", "Rejected"),
                ],
                default="new",
            ),
        ),
    ]
