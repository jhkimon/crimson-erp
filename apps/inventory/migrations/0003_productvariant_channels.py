from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_inventorysnapshot_inventorysnapshotitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="channels",
            field=models.JSONField(default=list, blank=True),
        ),
    ]

