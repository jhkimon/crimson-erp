from django.db import migrations


def backfill_categories(apps, schema_editor):
    InventoryItem = apps.get_model("inventory", "InventoryItem")
    InventoryCategory = apps.get_model("inventory", "InventoryCategory")

    names = (
        InventoryItem.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
    )
    for name in names:
        if name:
            InventoryCategory.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_create_inventorycategory"),
    ]

    operations = [
        migrations.RunPython(backfill_categories, migrations.RunPython.noop),
    ]

