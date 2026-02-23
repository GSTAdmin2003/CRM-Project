from django.db import migrations


def fix_settings_url_name(apps, schema_editor):
    AppRegistry = apps.get_model('core', 'AppRegistry')
    AppRegistry.objects.filter(name='settings').update(url_name='settings:home')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_user_extension'),
    ]

    operations = [
        migrations.RunPython(fix_settings_url_name, migrations.RunPython.noop),
    ]
