from django.db import models

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
    variant_id = models.CharField(max_length=255)
    supplier_id = models.IntegerField()
    quantity = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default=STATUS_PENDING
    )
    order_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
        managed = True

    def __str__(self):
        return f"Order #{self.id} - {self.status}"