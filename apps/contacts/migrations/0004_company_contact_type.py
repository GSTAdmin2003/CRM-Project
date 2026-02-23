from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0003_add_preferred_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="contact_type",
            field=models.CharField(
                choices=[("company", "Company"), ("individual", "Individual")],
                default="company",
                max_length=20,
                verbose_name="Contact Type",
            ),
        ),
    ]
