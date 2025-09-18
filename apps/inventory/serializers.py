from rest_framework import serializers
from .models import (
    InventoryItem, ProductVariant, 
    InventoryAdjustment, InventorySnapshot, InventorySnapshotItem
)
from apps.supplier.models import SupplierVariant


class ProductOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ['id', 'product_id', 'name']

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class ProductVariantSerializer(serializers.ModelSerializer):

    suppliers = serializers.SerializerMethodField()
    cost_price = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    product_id = serializers.CharField(source='product.product_id', read_only=True)
    stock = serializers.IntegerField(read_only=True)
    sales = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    channels = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'product_id',    # product_id
            'name',             # 상품명
            'category',         # 상품 카테고리
            'variant_code',         # variant_code
            'option',               # 옵션
            'stock',                # 재고량
            'price',                # 가격
            'min_stock',             # 최소재고
            'description',          # 상품설명
            'memo',                  # 메모
            'cost_price',           # 원가
            'order_count',          # 판매수량
            'return_count',          # 환불수량
            'sales',
            'suppliers',            # 공급자명
            'channels',             # 온라인/오프라인 태그
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        # POST, PUT, PATCH 요청 시에는 기본 정보 필드 입력 제거
        if request and request.method in ['POST', 'PUT', 'PATCH']:
            fields.pop('inventory_item', None)
            fields.pop('product_id', None)
        return fields

    def create(self, validated_data):
        product = self.context.get('product')
        if product:
            validated_data['product'] = product
        return ProductVariant.objects.create(**validated_data)
    def get_suppliers(self, obj):
        variants = SupplierVariant.objects.select_related("supplier").filter(variant=obj)
        return [
            {
                "name": sv.supplier.name,
                "is_primary": sv.is_primary,
                "cost_price": sv.cost_price,
            }
            for sv in variants
        ]
    def get_cost_price(self, obj):
        supplier_variants = SupplierVariant.objects.filter(variant=obj)
        prices = [sv.cost_price for sv in supplier_variants if sv.cost_price is not None]
        if not prices:
            return None
        return sum(prices) // len(prices)
    
    def get_sales(self, obj):
        return obj.price * (obj.order_count - obj.return_count)
    
    def get_name(self, obj):
        return obj.product.name if obj.product else None
    
    def get_category(self, obj):
        return obj.product.category if obj.product else None


# 간단한 응답용 시리얼라이저들
    
class InventoryItemWithVariantsSerializer(serializers.ModelSerializer):
    variants = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = ['product_id', 'name', 'variants']

    def get_variants(self, obj):
        active_variants = obj.variants.filter(is_active=True)
        return ProductVariantSerializer(active_variants, many=True, context=self.context).data

###### Create Update Delete를 위한 Serializer
class SupplierVariantUpdateSerializer(serializers.Serializer):
    name = serializers.CharField()
    cost_price = serializers.IntegerField()
    is_primary = serializers.BooleanField()

    def validate_name(self, value):
        from apps.supplier.models import Supplier
        try:
            return Supplier.objects.get(name=value)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError(f"공급자 '{value}'는 존재하지 않습니다.")

class ProductVariantFullUpdateSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(source="product.product_id", read_only=True)
    name = serializers.CharField(source="product.name", required=False)
    suppliers = SupplierVariantUpdateSerializer(many=True, required=False)
    option = serializers.CharField(required=False)
    category = serializers.CharField(write_only=True, required=False) # write-only 입력용
    category_name = serializers.CharField(source="product.category", read_only=True) # read-only 출력용

    class Meta:
        model = ProductVariant
        fields = [
            'product_id', 'variant_code', 'category', 'category_name', 'option', 'stock', 'price',
            'min_stock', 'description', 'memo',
            'name', 'suppliers'
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')

        # POST나 PATCH 요청 시 variant_code 제거
        if request and request.method in ['POST', 'PATCH']:
            fields.pop('variant_code', None)
        return fields

    def create(self, validated_data):
        product = self.context.get('product')
        validated_data.pop('product', None)

        # category 처리
        category_value = validated_data.pop('category', None)
        if category_value:
            product.category = category_value
            product.save()

        # suppliers 분리
        suppliers_data = validated_data.pop('suppliers', [])

        # variant 생성
        variant = ProductVariant.objects.create(product=product, **validated_data)

        # suppliers 연결
        for s in suppliers_data:
            SupplierVariant.objects.create(
                variant=variant,
                supplier=s['name'],
                cost_price=s['cost_price'],
                is_primary=s.get('is_primary', False),
            )
        return variant
    
    def update(self, instance, validated_data):
        # Update ProductVariant fields
        product_data = validated_data.pop('product', None)
        if isinstance(product_data, dict) and 'name' in product_data:
            instance.product.name = product_data['name']
            instance.product.save()

        # 카테고리 업데이트
        category_value = validated_data.pop('category', None)
        if category_value:
            instance.product.category = category_value
            instance.product.save()

        # 공급자 업데이트
        suppliers_data = validated_data.pop('suppliers', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update SupplierVariants
        if suppliers_data is not None:
            # 기존 관계 제거
            SupplierVariant.objects.filter(variant=instance).delete()

            # 새로 추가
            for s in suppliers_data:
                SupplierVariant.objects.create(
                    variant=instance,
                    supplier=s['name'],
                    cost_price=s['cost_price'],
                    is_primary=s.get('is_primary', False),
                )
        return instance
    
# Swagger용
class ProductVariantCreateSerializer(ProductVariantFullUpdateSerializer):
    class Meta(ProductVariantFullUpdateSerializer.Meta):
        fields = [f for f in ProductVariantFullUpdateSerializer.Meta.fields if f != 'variant_code']

# 재고조정용 Serailizer
class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(source='variant.variant_code', read_only=True)
    product_id = serializers.CharField(source='variant.product.product_id', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = [
            'id',
            'variant_code',
            'product_id',
            'product_name',
            'delta',
            'reason',
            'created_by',
            'created_at',
        ]
        read_only_fields = fields

class InventorySnapshotItemSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(source="variant.variant_code", read_only=True)
    option = serializers.CharField(source="variant.option", read_only=True)

    class Meta:
        model = InventorySnapshotItem
        fields = [
            "id",
            "variant",        # FK id (nullable)
            "product_id",
            "name",
            "category",
            "variant_code",
            "option",
            "stock",
            "price",
            "cost_price",
            "order_count",
            "return_count",
            "sales",
        ]
        read_only_fields = fields


class InventorySnapshotSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    items = InventorySnapshotItemSerializer(many=True, read_only=True)

    class Meta:
        model = InventorySnapshot
        fields = ["id", "created_at", "reason", "actor_name", "meta", "items"]
        
    def get_actor_name(self, obj):
            if obj.actor and obj.actor.first_name:
                return obj.actor.first_name
            return getattr(obj.actor, "username", None)
