from django.db import migrations


def seed_sales_manager_role(apps, schema_editor):
    Role = apps.get_model("core", "Role")
    Role.objects.get_or_create(
        name="Sales Manager",
        defaults={
            "description": "Sales manager — manages one or more sales teams and their members.",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_assign_user_extensions"),
    ]

    operations = [
        migrations.RunPython(seed_sales_manager_role, migrations.RunPython.noop),
    ]
