from django.db import migrations


def seed_sales_director_role(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    Role.objects.get_or_create(
        name='Sales Director',
        defaults={
            'description': 'Sales director — manages global pipeline stages and oversees all sales teams.',
            'is_active': True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_seed_it_admin_role'),
    ]

    operations = [
        migrations.RunPython(seed_sales_director_role, migrations.RunPython.noop),
    ]
