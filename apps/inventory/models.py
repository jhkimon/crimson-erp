from django.db import models


class InventoryItem(models.Model):
    product_code = models.CharField(
        max_length=50, unique=True, default="P00000")
    name = models.CharField(max_length=255)
    # 무슨 카테고리가 있는지 몰라서 우선을 수기로 입력하도록 조치함. 나중에는 DB에서 카테고리값 불러와서 동작하도록 고치면 될듯
    category = models.CharField(
        max_length=50,
        default="일반",
        help_text="상품 카테고리 (예: 문구, 도서, 의류 등)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # 병합 후 비활성화 처리용

    class Meta:
        db_table = "products"

    def __str__(self):
        # 호출 시 '상품코드 - 상품명' 형태로 반환
        return f"{self.product_code} - {self.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="variatns")
    variant_code = models.CharField(max_length=50, unique=True)
    option = models.CharField(max_length=255)
    stock = models.PositiveIntegerField()
    # 임시 재고 조정값 (재고 불일치 보정용)
    adjustment = models.IntegerField(
        default=0
    )
    price = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_variants"

    def __str__(self):
        # 객체 호출 시 '(상품 상세코드)(옵션)' 으로 반환환
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
