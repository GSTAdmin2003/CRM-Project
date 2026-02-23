from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0007_unify_lead_incominglead"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesteam",
            name="pitch_pdf",
            field=models.FileField(blank=True, upload_to="pitch_pdfs/", verbose_name="Pitch PDF"),
        ),
        migrations.AddField(
            model_name="salesteam",
            name="pitch_pdf_media_id",
            field=models.CharField(blank=True, max_length=200, verbose_name="Pitch PDF Media ID"),
        ),
        migrations.AddField(
            model_name="salesteam",
            name="pitch_pdf_filename",
            field=models.CharField(blank=True, max_length=200, verbose_name="Pitch PDF Filename"),
        ),
    ]
