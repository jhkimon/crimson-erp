from django.db import models
from apps.inventory.models import ProductVariant

class Order(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_CANCELLED = 'CANCELLED'

    ORDER_STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    id = models.AutoField(primary_key=True)
    variant = models.ForeignKey(
        ProductVariant,
        to_field='variant_code',
        db_column='variant_id',
        on_delete=models.CASCADE,
        null=True
    )
    supplier_id = models.IntegerField()
    quantity = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default=STATUS_PENDING
    )
    order_date = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'orders'
        managed = True

    def __str__(self):
        return f"Order #{self.id} - {self.status}"