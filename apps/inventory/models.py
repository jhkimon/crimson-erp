from django.conf import settings
from django.db import models
from django.conf import settings
from django.utils import timezone

def current_year():
    return timezone.now().year

def current_month():
    return timezone.now().month


######
# ProductVariantStatus + InventoryItem + ProductVariant = 엑셀 화면

class InventoryItem(models.Model):
    product_id = models.CharField(max_length=50, unique=True, default="P00000")
    big_category = models.CharField(max_length=50, blank=True)   # 대분류
    middle_category = models.CharField(max_length=50, blank=True)  # 중분류
    category = models.CharField(max_length=50, default="일반") # 카테고리
    description = models.CharField(max_length=255, blank=True)     # 설명
    name = models.CharField(max_length=255, blank=True) # 오프라인 이름
    online_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    management_code = models.CharField(max_length=50, blank=True, null=True) # 사용 안 함, DB 유지용으로 남김.
    is_active = models.BooleanField(default=True)
  

    class Meta:
        db_table = "products"
        ordering = ["product_id"]

    def __str__(self):
        return f"{self.product_id} - {self.name}"


# Product (Snapshot - 정적인 정보)
class ProductVariant(models.Model):
    product = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="variants"
    )  
    option = models.CharField(max_length=255) # 옵션
    detail_option = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )  # 상세옵션 (주로 사이즈)
    variant_code = models.CharField(max_length=50, unique=True)

    min_stock = models.PositiveIntegerField(default=0) # 재고 알림용

    description = models.TextField(blank=True, default="")
    channels = models.JSONField(default=list, blank=True)

    memo = models.TextField(blank=True, default="")
    cost_price = models.PositiveIntegerField(default=0) # 원가 (order 원가 저장용)
    price = models.PositiveIntegerField(default=0) # 판매가

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ### 안 쓰는 칼럼 주의 ###
    stock = models.IntegerField(default=0) # 안 쓰는 옛날 레퍼런스용 칼럼.
    adjustment = models.IntegerField(default=0) # 임시 재고 조정값 (재고 불일치 보정용, 현재는 안 씀.)
    order_count = models.PositiveIntegerField(default=0) # order은 별도 칼럼에서 계산
    return_count = models.PositiveIntegerField(default=0) # 환불 기록 안 함.
    is_active = models.BooleanField(default=True)


    class Meta:
        unique_together = ("product", "option", "detail_option")
        db_table = "product_variants"
        ordering = ["variant_code"]

    def __str__(self):
        return f"{self.variant_code}({self.option})"

# Product (Active - 동적인 정보)
class ProductVariantStatus(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()

    product = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)

    warehouse_stock_start = models.IntegerField(default=0)  # 월초창고
    store_stock_start = models.IntegerField(default=0)      # 월초매장

    inbound_quantity = models.IntegerField(default=0)       # 당월입고 (나중에 order가 해당 내용 조정)

    store_sales = models.IntegerField(default=0)            # 매장판매
    online_sales = models.IntegerField(default=0)           # 쇼핑몰판매

    created_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(default=0)

    class Meta:
        unique_together = ("year", "month", "variant")



# 재고 조정용 필드
class InventoryAdjustment(models.Model):
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="adjustments"
    )
    year = models.IntegerField(default=current_year)
    month = models.IntegerField(default=current_month)
    delta = models.IntegerField(help_text="보정 수량: 양수/음수 모두 가능")
    reason = models.CharField(max_length=255, help_text="보정 사유 설명")
    created_by = models.CharField(
        max_length=50, help_text="보정 작업 수행자(사용자명 또는 ID)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_adjustments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Adjustment for {self.variant.variant_code}: {self.delta}"
    