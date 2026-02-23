from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0004_company_contact_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="preferred_language",
            field=models.CharField(
                blank=True,
                choices=[("en", "English"), ("ka", "Georgian")],
                default="",
                max_length=10,
                verbose_name="Preferred Pitch Language",
            ),
        ),
    ]
