import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0002_add_default_activity_types"),
        ("crm", "0006_lead_email_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="lead",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="scheduled_activities",
                to="crm.lead",
                verbose_name="Opportunity",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="incoming_lead",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="activities",
                to="crm.incominglead",
                verbose_name="Lead",
            ),
        ),
    ]
