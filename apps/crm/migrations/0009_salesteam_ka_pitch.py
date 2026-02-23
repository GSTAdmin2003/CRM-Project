from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0008_salesteam_pitch_pdf"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesteam",
            name="pitch_pdf_ka",
            field=models.FileField(blank=True, upload_to="pitch_pdfs/", verbose_name="Pitch PDF (Georgian)"),
        ),
        migrations.AddField(
            model_name="salesteam",
            name="pitch_pdf_media_id_ka",
            field=models.CharField(blank=True, max_length=200, verbose_name="Pitch PDF Media ID (Georgian)"),
        ),
        migrations.AddField(
            model_name="salesteam",
            name="pitch_pdf_filename_ka",
            field=models.CharField(blank=True, max_length=200, verbose_name="Pitch PDF Filename (Georgian)"),
        ),
    ]
