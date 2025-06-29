from django.db import models
from apps.inventory.models import ProductVariant


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    manager = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=255)

    # 여러 ProductVariant를 공급
    variants = models.ManyToManyField(
        'inventory.ProductVariant', 
        through='SupplierVariant',
        related_name='suppliers')
    def __str__(self):
        return self.name


class SupplierVariant(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)

    cost_price = models.PositiveIntegerField(default=0)
    lead_time_days = models.IntegerField(default=3)
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ('supplier', 'variant')