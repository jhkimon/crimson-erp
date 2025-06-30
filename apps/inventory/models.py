from django.db import models

class InventoryItem(models.Model):
    product_id = models.CharField(max_length=50, unique=True, default="P00000")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return f"{self.product_id} - {self.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="variants")
    variant_code = models.CharField(max_length=50, unique=True)
    option = models.CharField(max_length=255)
    
    stock = models.PositiveIntegerField()
    min_stock = models.PositiveIntegerField(default=0) 
    price = models.PositiveIntegerField()

    description = models.TextField(blank=True, null=True)
    memo = models.TextField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    order_count = models.PositiveIntegerField(default=0)
    return_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product_variants"

    def __str__(self):
        return f"{self.variant_code}({self.option})"