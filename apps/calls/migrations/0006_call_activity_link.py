# Generated migration: 0006_call_activity_link
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0004_unify_lead_incominglead"),
        ("calls", "0005_add_schedule_and_sounds"),
    ]

    operations = [
        migrations.AddField(
            model_name="call",
            name="activity",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="call",
                to="activities.activity",
            ),
        ),
    ]
