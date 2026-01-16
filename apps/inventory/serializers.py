from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone

from apps.inventory.utils.variant_code import build_variant_code


from .models import (
    InventoryItem,
    ProductVariant,
    InventoryAdjustment,
    ProductVariantStatus
)

####### Base Serializer: InventoryItem, ProductVariant, InventoryAdjustment
class InventoryItemSummarySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "variant_code",
            "name",
        ]

    def get_name(self, obj):
        product_name = obj.product.name
        option = obj.option
        detail_option = obj.detail_option

        if detail_option:
            return f"{product_name} ({option}, {detail_option})"
        return f"{product_name} ({option})"

class ProductVariantSerializer(serializers.ModelSerializer):

    product_id = serializers.CharField(source="product.product_id", read_only=True)
    offline_name = serializers.CharField(source="product.name", read_only=True)
    online_name = serializers.CharField(source="product.online_name", read_only=True)

    big_category = serializers.CharField(source="product.big_category", read_only=True)
    middle_category = serializers.CharField(source="product.middle_category", read_only=True)
    category = serializers.CharField(source="product.category", read_only=True)
    description = serializers.CharField(source="product.description", read_only=True)

    detail_option = serializers.CharField(read_only=True)
    # stock = serializers.SerializerMethodField()
    channels = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "product_id",  # product_id
            "offline_name",
            "online_name",
            "big_category",
            "middle_category",
            "category",  # 상품 카테고리
            "variant_code",  # variant_code
            "option",  # 옵션
            "detail_option",
            # "stock",
            "price",  # 가격
            # "min_stock",  # 최소재고
            "description",  # 상품설명
            "memo",  # 메모
            "channels",  # 온라인/오프라인 태그
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        return fields


    def get_stock(self, obj):
        today = timezone.now()
        year = today.year
        month = today.month

        try:
            status = ProductVariantStatus.objects.get(
                variant=obj,
                year=year,
                month=month,
            )
        except ProductVariantStatus.DoesNotExist:
            return 0

        initial_stock = (
            status.warehouse_stock_start + status.store_stock_start
        )
        total_sales = status.store_sales + status.online_sales

        adjustment_quantity = (
            InventoryAdjustment.objects.filter(
                variant=obj,
                year=year,
                month=month,
            ).aggregate(total=Sum("delta"))["total"]
            or 0
        )

        return (
            initial_stock
            + status.inbound_quantity
            - total_sales
            + adjustment_quantity
        )

class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(source="variant.variant_code", read_only=True)
    product_id = serializers.CharField(
        source="variant.product.product_id", read_only=True
    )
    product_name = serializers.CharField(source="variant.product.name", read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = [
            "id",
            "variant_code",
            "product_id",
            "product_name",
            "delta",
            "reason",
            "created_by",
            "created_at",
        ]
        read_only_fields = fields

class ProductVariantStatusSerializer(serializers.ModelSerializer):
    """
    엑셀 한 행을 그대로 표현하기 위한 Serializer
    ProductVariantStatus + InventoryItem + ProductVariant 조인 결과
    """

    # 상단 기본 정보
    big_category = serializers.CharField(source="product.big_category", read_only=True)     # 대분류
    middle_category = serializers.CharField(source="product.middle_category", read_only=True)  # 중분류
    category = serializers.CharField(source="product.category", read_only=True)              # 카테고리
    description = serializers.CharField(source="product.description", read_only=True)        # 설명

    online_name = serializers.CharField(source="product.online_name", read_only=True)
    offline_name = serializers.CharField(source="product.name", read_only=True)

    option = serializers.CharField(source="variant.option", read_only=True)
    detail_option = serializers.CharField(source="variant.detail_option", read_only=True)
    product_code = serializers.CharField(source="product.product_id", read_only=True)
    variant_code = serializers.CharField(source="variant.variant_code", read_only=True)

    # 계산 필드
    initial_stock = serializers.SerializerMethodField()    # 기초재고
    total_sales = serializers.SerializerMethodField()      # 판매물량 합
    adjustment_quantity = serializers.SerializerMethodField()
    adjustment_status = serializers.SerializerMethodField() 
    ending_stock = serializers.SerializerMethodField()     # 기말재고

    class Meta:
        model = ProductVariantStatus
        fields = [
            # 메타 정보
            "year",
            "month",

            # 상품 관련
            "big_category",
            "middle_category",
            "category",
            "description",
            "online_name",
            "offline_name",
            "option",
            "detail_option",
            "product_code",
            "variant_code",

            # 수량 정보
            "warehouse_stock_start",
            "store_stock_start",
            "initial_stock",
            "inbound_quantity",
            "store_sales",
            "online_sales",
            "total_sales",
            "adjustment_quantity",
            "adjustment_status",
            "ending_stock",
            "version"
        ]

    def get_initial_stock(self, obj):
        # 기초재고 = 월초창고 + 월초매장
        return obj.warehouse_stock_start + obj.store_stock_start

    def get_total_sales(self, obj):
        # 판매물량 합 = 매장 판매 + 온라인 판매
        return obj.store_sales + obj.online_sales

    def get_adjustment_quantity(self, obj):
        # 재고조정 합
        return (
            InventoryAdjustment.objects.filter(
                variant=obj.variant,
                year=obj.year,
                month=obj.month,
            ).aggregate(total=Sum("delta"))["total"]
            or 0
        )
    
    def get_adjustment_status(self, obj):
        """
        adjustment_status = [{책임자, quantity}, ...]
        """
        adjustments = InventoryAdjustment.objects.filter(
            variant=obj.variant,
            year=obj.year,
            month=obj.month,
        ).values("created_by", "delta")

        return [
            {
                "created_by": adj["created_by"],
                "quantity": adj["delta"],
            }
            for adj in adjustments
        ]


    def get_ending_stock(self, obj):
        # 기초재고 - 판매물량 합 + 재고 조정 합
        return (
            self.get_initial_stock(obj)
            + obj.inbound_quantity
            - self.get_total_sales(obj)
            + self.get_adjustment_quantity(obj)
        )

####### 변형 Serializer: InventoryItem (+ ProductVariant)

class InventoryItemWithVariantsSerializer(serializers.ModelSerializer):
    variants = serializers.SerializerMethodField()
    class Meta:
        model = InventoryItem
        fields = ["product_id", "name", "variants"]

    def get_variants(self, obj):
        active_variants = obj.variants.filter(is_active=True)
        return ProductVariantSerializer(
            active_variants, many=True, context=self.context
        ).data


#######  ProductVariant 쓰기 & 수정
class ProductVariantWriteSerializer(serializers.ModelSerializer):
    """
    ProductVariant 생성/수정용 Serializer

    - Product 관련 필드는 source="product.xxx" 로 전달
    - Variant 생성 시 variant_code는 자동 생성
    """

    # ===== Product fields =====
    product_id = serializers.CharField(
        source="product.product_id",
        read_only=True,
    )
    name = serializers.CharField(
        source="product.name",
        required=False,
    )
    online_name = serializers.CharField(
        source="product.online_name",
        required=False,
        allow_blank=True,
    )
    big_category = serializers.CharField(
        source="product.big_category",
        required=False,
        allow_blank=True,
    )
    middle_category = serializers.CharField(
        source="product.middle_category",
        required=False,
        allow_blank=True,
    )
    category = serializers.CharField(
        write_only=True,
        required=False,
    )
    category_name = serializers.CharField(
        source="product.category",
        read_only=True,
    )

    # ===== Variant fields =====
    option = serializers.CharField(required=False)
    detail_option = serializers.CharField(required=False, allow_blank=True)

    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=["online", "offline"]),
        required=False,
        allow_empty=True,
    )
    class Meta:
        model = ProductVariant
        fields = [
            "product_id",
            "variant_code",
            "category",
            "category_name",
            "option",
            "detail_option",
            "price",
            "min_stock",
            "description",
            "memo",
            "name",
            "online_name",
            "big_category",
            "middle_category",
            "channels"
        ]

    # ==========================
    # variant_code는 클라이언트 입력 금지
    # ==========================
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")

        if request and request.method in ("POST", "PATCH"):
            fields.pop("variant_code", None)

        return fields

    # ==========================
    # CREATE
    # ==========================
    def create(self, validated_data):
        product = self.context["product"]
        today = timezone.now()

        # 🔹 Product 필드 처리
        product_data = validated_data.pop("product", {})
        category_value = validated_data.pop("category", None)

        for attr, value in product_data.items():
            setattr(product, attr, value)

        if category_value:
            product.category = category_value

        product.save()

        # 🔹 Variant 필드
        channels = validated_data.pop("channels", None)

        option = validated_data.get("option", "")
        detail_option = validated_data.get("detail_option", "")

        validated_data["variant_code"] = build_variant_code(
            product_id=product.product_id,
            product_name=product.name,
            option=option,
            detail_option=detail_option,
            allow_auto=False, 
        )

        variant = ProductVariant.objects.create(
            product=product,
            **validated_data,
        )

        if channels is not None:
            variant.channels = channels
            variant.save(update_fields=["channels"])
        
        ProductVariantStatus.objects.get_or_create(
            variant=variant,
            year=today.year,
            month=today.month,
            defaults={
                "product": product,
                "warehouse_stock_start": 0,
                "store_stock_start": 0,
                "inbound_quantity": 0,
                "store_sales": 0,
                "online_sales": 0,
            },
        )

        return variant

    # ==========================
    # UPDATE
    # ==========================
    def update(self, instance, validated_data):
        product = instance.product

        # 🔹 Product 필드
        product_data = validated_data.pop("product", {})
        category_value = validated_data.pop("category", None)

        for attr, value in product_data.items():
            setattr(product, attr, value)

        if category_value:
            product.category = category_value

        if product_data or category_value:
            product.save()

        # 🔹 Variant 필드
        channels = validated_data.pop("channels", None)
        dirty_fields = []

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            dirty_fields.append(attr)

        if channels is not None:
            instance.channels = channels
            dirty_fields.append("channels")

        if dirty_fields:
            instance.save(update_fields=list(dict.fromkeys(dirty_fields)))

        return instance

    
class ProductVariantStatusPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariantStatus
        fields = [
            "warehouse_stock_start",
            "store_stock_start",
            "inbound_quantity",
            "store_sales",
            "online_sales"
        ]


### InventoryAdjustment
class InventoryAdjustmentCreateSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(write_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = [
            "variant_code",
            "year",
            "month",
            "delta",
            "reason"
        ]

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        variant_code = validated_data.pop("variant_code")

        try:
            variant = ProductVariant.objects.get(
                variant_code=variant_code,
                is_active=True
            )
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError(
                {"variant_code": "존재하지 않거나 비활성화된 상품 옵션입니다."}
            )

        created_by = (
            user.get_full_name()
            if user.get_full_name()
            else user.username
        )

        return InventoryAdjustment.objects.create(
            variant=variant,
            created_by=created_by,
            **validated_data
        )