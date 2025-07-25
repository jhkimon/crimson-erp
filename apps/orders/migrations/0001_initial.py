# Generated by Django 4.2.20 on 2025-07-23 10:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('supplier', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('order_date', models.DateField()),
                ('expected_delivery_date', models.DateField(blank=True, null=True)),
                ('vat_included', models.BooleanField(default=True)),
                ('packaging_included', models.BooleanField(default=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('CANCELLED', 'Cancelled'), ('COMPLETED', 'Completed')], default='PENDING', max_length=20)),
                ('instruction_note', models.TextField(blank=True, null=True)),
                ('note', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_orders', to=settings.AUTH_USER_MODEL)),
                ('supplier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='supplier.supplier')),
            ],
            options={
                'db_table': 'orders',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=255)),
                ('spec', models.CharField(blank=True, max_length=100, null=True)),
                ('unit', models.CharField(default='EA', max_length=20)),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.PositiveIntegerField()),
                ('remark', models.CharField(blank=True, max_length=255, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.productvariant')),
            ],
            options={
                'db_table': 'order_items',
            },
        ),
    ]
