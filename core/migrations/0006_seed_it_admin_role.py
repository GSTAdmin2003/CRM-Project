from django.db import migrations


def seed_it_admin_role(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    Role.objects.get_or_create(
        name='IT Admin',
        defaults={
            'description': 'IT administrator — manages VoIP configuration, system infrastructure, and technical settings.',
            'is_active': True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_fix_settings_app_url_name'),
    ]

    operations = [
        migrations.RunPython(seed_it_admin_role, migrations.RunPython.noop),
    ]
