# Generated by Django 4.2.20 on 2025-03-13 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_productvariant'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
