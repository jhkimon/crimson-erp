# Generated by Django 4.2.20 on 2025-07-06 04:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0002_employee_full_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='inactive', max_length=10),
        ),
    ]
