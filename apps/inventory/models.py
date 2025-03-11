from django.db import models

class InventoryItem(models.Model):
    product_id = models.CharField(max_length=50, unique=True, default="P00000")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"