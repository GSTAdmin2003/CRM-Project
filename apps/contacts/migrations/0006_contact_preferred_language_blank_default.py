from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0005_company_preferred_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
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
