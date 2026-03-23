from django.db import migrations


def rename_sales_manager(apps, schema_editor):
    Role = apps.get_model("core", "Role")
    Role.objects.filter(name="Sales Manager").update(
        name="Team Manager",
        description="Team manager — manages one or more sales teams and their members.",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_seed_sales_manager_role"),
    ]

    operations = [
        migrations.RunPython(rename_sales_manager, migrations.RunPython.noop),
    ]
