from django.db import models
from django.conf import settings
from django.utils import timezone

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

class InventorySnapshot(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    reason = models.CharField(max_length=200, blank=True, help_text="스냅샷 사유 (예: POS 덮어쓰기 전)")
    actor = models.ForeignKey(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="inventory_snapshots",
    )
    meta = models.JSONField(default=dict, blank=True)  # 요청 payload, 파일명 등 부가정보

    def __str__(self):
        return f"Snapshot#{self.id} @ {self.created_at:%Y-%m-%d %H:%M:%S} ({self.reason}) by {actor_name}"


class InventorySnapshotItem(models.Model):
    snapshot = models.ForeignKey(InventorySnapshot, on_delete=models.CASCADE, related_name="items")

    variant = models.ForeignKey("ProductVariant", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="+")
    # 스냅샷 시점의 값(denormalized)
    product_id   = models.CharField(max_length=32, db_index=True)
    name         = models.CharField(max_length=255)
    category     = models.CharField(max_length=64)
    variant_code = models.CharField(max_length=64, db_index=True)
    option       = models.CharField(max_length=255, blank=True)

    stock       = models.IntegerField()
    price       = models.IntegerField()
    cost_price  = models.IntegerField()
    order_count = models.IntegerField(default=0)
    return_count= models.IntegerField(default=0)
    sales       = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["snapshot", "variant_code"]),
            models.Index(fields=["product_id"]),
        ]