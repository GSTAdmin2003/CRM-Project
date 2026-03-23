from django.db import migrations


def rename_to_sales_manager(apps, schema_editor):
    Role = apps.get_model("core", "Role")
    Role.objects.filter(name="Team Manager").update(
        name="Sales Manager",
        description="Sales manager — manages one or more sales teams and their members.",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_rename_sales_manager_to_team_manager"),
    ]

    operations = [
        migrations.RunPython(rename_to_sales_manager, migrations.RunPython.noop),
    ]
