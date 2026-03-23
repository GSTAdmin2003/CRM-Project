from django.db import migrations


def assign_extensions(apps, schema_editor):
    User = apps.get_model("core", "User")
    users = list(User.objects.filter(extension="").order_by("date_joined", "id"))
    # Find highest existing numeric extension
    existing = [
        int(u.extension)
        for u in User.objects.exclude(extension="")
        if u.extension.isdigit()
    ]
    next_ext = max(existing) + 1 if existing else 100
    for user in users:
        user.extension = str(next_ext)
        user.save(update_fields=["extension"])
        next_ext += 1


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_seed_sales_director_role"),
    ]

    operations = [
        migrations.RunPython(assign_extensions, migrations.RunPython.noop),
    ]
