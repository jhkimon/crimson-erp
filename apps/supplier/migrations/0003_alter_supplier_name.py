# Generated by Django 4.2.20 on 2025-07-03 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0002_suppliervariant_cost_price_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplier',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
