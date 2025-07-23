from django.db import models
from apps.inventory.models import ProductVariant
from apps.supplier.models import Supplier 
from django.utils import timezone
from apps.hr.models import Employee

# 발주 자체
class Order(models.Model):
    # STEP 1: 발주서 작성
    STATUS_PENDING = 'PENDING'
    # STEP 2: 승인 또는 취소
    STATUS_APPROVED = 'APPROVED'
    STATUS_CANCELLED = 'CANCELLED'
    # STEP 3: 완료 -> 재고 반영
    STATUS_COMPLETED = 'COMPLETED'

    ORDER_STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='orders', null=True)
    order_date = models.DateField()  # 수기 입력 가능성 고려
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_orders'
    )
    expected_delivery_date = models.DateField(null=True, blank=True)

    vat_included = models.BooleanField(default=True)
    packaging_included = models.BooleanField(default=True)

    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default=STATUS_PENDING)
    instruction_note = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.supplier.name}"

# 상품
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    
    item_name = models.CharField(max_length=255) # Variant 삭제 대비하여 저장
    spec = models.CharField(max_length=100, null=True, blank=True)  # ex. 300ml
    unit = models.CharField(max_length=20, default='EA')
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    remark = models.CharField(max_length=255, blank=True, null=True)

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    class Meta:
        db_table = 'order_items'