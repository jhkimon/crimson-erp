from django.db import models

class Order(models.Model):
    id = models.AutoField(primary_key=True)  # Let Django automatically manage the primary key
    variant_id = models.CharField(max_length=255)
    supplier_id = models.IntegerField()
    quantity = models.IntegerField()
    status = models.CharField(max_length=10)
    order_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'  # Maps to the PostgreSQL table 'orders'
        managed = True
