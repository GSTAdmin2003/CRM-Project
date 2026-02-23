from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_settings", "0003_unify_lead_incominglead"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userpreferences",
            name="language",
            field=models.CharField(
                choices=[("en", "English"), ("ka", "Georgian")],
                default="en",
                max_length=5,
            ),
        ),
    ]
