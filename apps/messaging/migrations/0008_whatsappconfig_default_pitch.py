from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0007_rename_en_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappconfig',
            name='default_pitch_media_id',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='default_pitch_filename',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='default_pitch_media_id_ka',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='default_pitch_filename_ka',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
