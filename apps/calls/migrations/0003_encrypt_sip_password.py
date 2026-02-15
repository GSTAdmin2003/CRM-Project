# Rename password field to _password (db_column stays 'password')
# and change type to TextField, then encrypt existing plaintext passwords.

from django.db import migrations, models


def encrypt_existing_passwords(apps, schema_editor):
    """Encrypt any existing plaintext SIP passwords."""
    SIPSettings = apps.get_model('calls', 'SIPSettings')
    for sip in SIPSettings.objects.all():
        if sip.password:
            from apps.calls.encryption import encrypt
            sip.password = encrypt(sip.password)
            sip.save(update_fields=['password'])


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0002_add_sip_settings'),
    ]

    operations = [
        # Rename the Python field; db_column='password' keeps the column name
        migrations.RenameField(
            model_name='sipsettings',
            old_name='password',
            new_name='_password',
        ),
        # Change from CharField(128) to TextField to hold encrypted data
        migrations.AlterField(
            model_name='sipsettings',
            name='_password',
            field=models.TextField(db_column='password', verbose_name='SIP Password'),
        ),
        # Encrypt existing plaintext passwords
        migrations.RunPython(encrypt_existing_passwords, migrations.RunPython.noop),
    ]
