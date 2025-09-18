from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_merge_20250912_1722"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryCategory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
            ],
            options={
                "db_table": "inventory_categories",
                "ordering": ["name"],
            },
        ),
    ]
