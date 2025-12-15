from rest_framework import serializers
from django.db.models import Sum

from apps.inventory.utils.variant_code import generate_variant_code

from .models import (
    InventoryItem,
    ProductVariant,
    InventoryAdjustment,
    ProductVariantStatus
)

####### Base Serializer: InventoryItem, ProductVariant, InventoryAdjustment
class InventoryItemSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "product_id", "name"]

class ProductVariantSerializer(serializers.ModelSerializer):

    product_id = serializers.CharField(source="product.product_id", read_only=True)
    offline_name = serializers.CharField(source="product.name", read_only=True)
    online_name = serializers.CharField(source="product.online_name", read_only=True)

    big_category = serializers.CharField(source="product.big_category", read_only=True)
    middle_category = serializers.CharField(source="product.middle_category", read_only=True)
    category = serializers.CharField(source="product.category", read_only=True)
    description = serializers.CharField(source="product.description", read_only=True)

    stock = serializers.IntegerField(read_only=True)
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
            "stock",  # 재고량
            "price",  # 가격
            "min_stock",  # 최소재고
            "description",  # 상품설명
            "memo",  # 메모
            "channels",  # 온라인/오프라인 태그
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        return fields

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
    adjustment_total = serializers.SerializerMethodField() # 재고조정 합
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
            "adjustment_total",
            "ending_stock",
        ]

    def get_initial_stock(self, obj):
        # 기초재고 = 월초창고 + 월초매장
        return obj.warehouse_stock_start + obj.store_stock_start

    def get_total_sales(self, obj):
        # 판매물량 합 = 매장 판매 + 온라인 판매
        return obj.store_sales + obj.online_sales

    def get_adjustment_total(self, obj):
        # 재고조정 합
        return (
            InventoryAdjustment.objects.filter(
                variant=obj.variant,
                year=obj.year,
                month=obj.month,
            ).aggregate(total=Sum("delta"))["total"]
            or 0
        )

    def get_ending_stock(self, obj):
        # 기초재고 - 판매물량 합 + 재고 조정 합
        return (
            self.get_initial_stock(obj)
            + obj.inbound_quantity
            - self.get_total_sales(obj)
            + self.get_adjustment_total(obj)
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
    product_id = serializers.CharField(source="product.product_id", read_only=True)
    name = serializers.CharField(source="product.name", required=False)
    option = serializers.CharField(required=False)
    detail_option = serializers.CharField(required=False)
    category = serializers.CharField(
        write_only=True, required=False
    )
    category_name = serializers.CharField(
        source="product.category", read_only=True
    )
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
            "stock",
            "price",
            "min_stock",
            "description",
            "memo",
            "name",
            "channels",
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")

        # POST나 PATCH 요청 시 variant_code 제거
        if request and request.method in ["POST", "PATCH"]:
            fields.pop("variant_code", None)
        return fields

    def create(self, validated_data):
        product = self.context.get("product")
        validated_data.pop("product", None)

        # category 처리
        category_value = validated_data.pop("category", None)
        if category_value:
            product.category = category_value
            product.save(update_fields=["category"])

        channels = validated_data.pop("channels", None)

        # 🔥 핵심: variant_code 생성
        option = validated_data.get("option", "")
        detail_option = validated_data.get("detail_option", "")

        validated_data["variant_code"] = generate_variant_code(
            product.product_id,
            option,
            detail_option,
        )

        variant = ProductVariant.objects.create(
            product=product,
            **validated_data
        )

        if channels is not None:
            variant.channels = channels
            variant.save(update_fields=["channels"])

        return variant

    def update(self, instance, validated_data):
        # 카테고리 업데이트
        category_value = validated_data.pop("category", None)
        if category_value:
            instance.product.category = category_value
            instance.product.save()

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
            "reason",
            "created_by",
        ]

    def create(self, validated_data):
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


        return InventoryAdjustment.objects.create(
            variant=variant,
            **validated_data
        )
