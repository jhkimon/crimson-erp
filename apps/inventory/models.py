from django.conf import settings
from django.db import models

class InventoryItem(models.Model):
    product_id = models.CharField(max_length=50, unique=True, default="P00000")
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50,
        default="일반",
        help_text="상품 카테고리 (예: 문구, 도서, 의류 등)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # 병합 후 비활성화 처리용

    class Meta:
        db_table = "products"
        ordering = ["product_id"]

    def __str__(self):
        return f"{self.product_id} - {self.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="variants")
    variant_code = models.CharField(max_length=50, unique=True)
    option = models.CharField(max_length=255)
    
    stock = models.IntegerField(default=0)
    min_stock = models.PositiveIntegerField(default=0) 
    price = models.PositiveIntegerField(default=0)

    description = models.TextField(blank=True, default="")
    memo = models.TextField(blank=True, default="")
    cost_price = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 임시 재고 조정값 (재고 불일치 보정용)
    adjustment = models.IntegerField(
        default=0
    )

    @property
    def available_stock(self):
        """판매 가능한 실제 재고량"""
        return max(0, self.stock - self.reserved_stock)

    order_count = models.PositiveIntegerField(default=0)
    return_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_variants"
        ordering = ["variant_code"]

    def __str__(self):
        return f"{self.variant_code}({self.option})"


# 재고 조정용 필드
class InventoryAdjustment(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="adjustments"
    )
    delta = models.IntegerField(
        help_text="보정 수량: 양수/음수 모두 가능"
    )
    reason = models.CharField(
        max_length=255,
        help_text="보정 사유 설명"
    )
    created_by = models.CharField(
        max_length=50,
        help_text="보정 작업 수행자(사용자명 또는 ID)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_adjustments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Adjustment for {self.variant.variant_code}: {self.delta}"

class ImportBatch(models.Model):
    SHEET_VARIANT = 'variant_detail'
    SHEET_SALES = 'sales_summary'
    SHEET_CHOICES = [
        (SHEET_VARIANT, 'Variant Detail'),
        (SHEET_SALES, 'Sales Summary'),
    ]

    STATUS_APPLIED = 'applied'
    STATUS_ROLLED_BACK = 'rolled_back'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_ROLLED_BACK, 'Rolled Back'),
        (STATUS_FAILED, 'Failed'),
    ]

    file_name = models.CharField(max_length=255)
    sheet_type = models.CharField(max_length=32, choices=SHEET_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "import_batches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch#{self.id} {self.sheet_type} ({self.file_name}) - {self.status}"


class ImportChange(models.Model):
    ACTION_CREATE_PRODUCT = 'create_product'
    ACTION_UPDATE_PRODUCT = 'update_product'
    ACTION_CREATE_VARIANT = 'create_variant'
    ACTION_UPDATE_VARIANT = 'update_variant'
    ACTION_CHOICES = [
        (ACTION_CREATE_PRODUCT, 'Create Product'),
        (ACTION_UPDATE_PRODUCT, 'Update Product'),
        (ACTION_CREATE_VARIANT, 'Create Variant'),
        (ACTION_UPDATE_VARIANT, 'Update Variant'),
    ]

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='changes')

    # 어떤 대상이 변경됐는지 연결(없을 수도 있음: 스킵/실패 행 기록용)
    product = models.ForeignKey('InventoryItem', null=True, blank=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey('ProductVariant', null=True, blank=True, on_delete=models.SET_NULL)

    action = models.CharField(max_length=32, choices=ACTION_CHOICES)

    # 이전/이후 스냅샷, 가감치(옵션)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    deltas = models.JSONField(null=True, blank=True)

    # 엑셀 원본 행번호(1-based 등 가독용)
    row_index = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_changes"
        ordering = ["id"]