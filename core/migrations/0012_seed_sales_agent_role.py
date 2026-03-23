from django.db import migrations


def seed_sales_agent_role(apps, schema_editor):
    Role = apps.get_model("core", "Role")
    Role.objects.get_or_create(
        name="Sales Agent",
        defaults={
            "description": "Sales agent — handles assigned leads and opportunities within their team.",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_revert_to_sales_manager"),
    ]

    operations = [
        migrations.RunPython(seed_sales_agent_role, migrations.RunPython.noop),
    ]
