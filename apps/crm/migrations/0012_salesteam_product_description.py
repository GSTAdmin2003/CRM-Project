from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0011_salesteam_stt_keywords_per_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesteam",
            name="product_description",
            field=models.TextField(
                blank=True,
                verbose_name="Product Description",
                help_text="Description of the product or service this team sells.",
            ),
        ),
    ]
