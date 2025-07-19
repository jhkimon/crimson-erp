from django.db import models


class InventoryItem(models.Model):
    product_code = models.CharField(
        max_length=50, unique=True, default="P00000", db_column='product_id')
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
        InventoryItem, on_delete=models.CASCADE, related_name="variants")
    variant_code = models.CharField(max_length=50, unique=True)
    option = models.CharField(max_length=255)
    stock = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 임시 재고 조정값 (재고 불일치 보정용)
    adjustment = models.IntegerField(
        default=0
    )
    # 예약된 재고량 (실제 재고에서 차감되지 않은 상태)
    reserved_stock = models.PositiveIntegerField(default=0)

    @property
    def available_stock(self):
        """판매 가능한 실제 재고량"""
        return max(0, self.stock - self.reserved_stock)

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

# 온라인 POS 대응용 모델


class SalesChannel(models.Model):
    """판매 채널 관리 (온라인/오프라인)"""
    CHANNEL_CHOICES = [
        ('online', '온라인'),
        ('offline', '오프라인'),
        ('pos', 'POS'),
    ]

    name = models.CharField(max_length=100)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    webhook_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_channels"

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class SalesTransaction(models.Model):
    """판매 트랜잭션 관리"""
    STATUS_CHOICES = [
        ('pending', '결제 대기'),
        ('paid', '결제 완료'),
        ('cancelled', '주문 취소'),
        ('refunded', '환불 완료'),
    ]

    # POS/온라인몰 주문 ID
    external_order_id = models.CharField(max_length=100, unique=True)
    channel = models.ForeignKey(SalesChannel, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # 고객 정보 (필요시)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)

    total_amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_transactions"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.external_order_id} - {self.get_status_display()}"


class SalesTransactionItem(models.Model):
    """판매 트랜잭션 상품 상세"""
    transaction = models.ForeignKey(
        SalesTransaction,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField()

    # 재고 예약/차감 상태
    is_stock_reserved = models.BooleanField(default=False)
    is_stock_deducted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_transaction_items"

    def save(self, *args, **kwargs):
        # 자동으로 total_price 계산
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class StockReservation(models.Model):
    """재고 예약 관리"""
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    transaction_item = models.OneToOneField(
        SalesTransactionItem,
        on_delete=models.CASCADE
    )

    reserved_quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()  # 예약 만료 시간
    is_confirmed = models.BooleanField(default=False)  # 결제 완료시 True

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_reservations"

    def __str__(self):
        return f"{self.variant.variant_code} - {self.reserved_quantity}개 예약"
