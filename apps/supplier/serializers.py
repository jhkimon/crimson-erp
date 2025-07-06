from rest_framework import serializers
from apps.supplier.models import Supplier, SupplierVariant
from apps.inventory.models import ProductVariant


# 빠른 검색용
class SupplierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact', 'manager', 'email', 'address']

# Supplier <> Variant Mapping Table 읽기용
class SupplierVariantDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='variant.id')
    option = serializers.CharField(source='variant.option')
    stock = serializers.IntegerField(source='variant.stock')
    name = serializers.SerializerMethodField()

    class Meta:
        model = SupplierVariant
        fields = ['id', 'option', 'stock', 'name', 'cost_price', 'is_primary']

    def get_name(self, obj):
        return obj.variant.product.name
    
# Supplier <> Variant Mapping Table 수정용
class SupplierVariantUpdateTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierVariant
        fields = ['id', 'cost_price', 'is_primary']
        read_only_fields = ['id']  # id는 변경하지 않고 참조만 할 수 있게 설정

# Supplier 전체
class SupplierSerializer(serializers.ModelSerializer):
    # variant_codes는 입력용(write-only)
    variant_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    # variants는 출력용(read-only)
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact', 'manager', 'email', 'address',
            'variant_codes', 'variants'
        ]

    def get_variants(self, obj):
        supplier_variants = SupplierVariant.objects.filter(supplier=obj).select_related('variant__product')
        return SupplierVariantDetailSerializer(supplier_variants, many=True).data

    def create(self, validated_data):
        variant_codes = validated_data.pop('variant_codes', [])
        supplier = Supplier.objects.create(**validated_data)

        # 연결된 variants 생성
        variants = ProductVariant.objects.filter(variant_code__in=variant_codes)
        for variant in variants:
            SupplierVariant.objects.create(supplier=supplier, variant=variant)

        return supplier

    def update(self, instance, validated_data):
        variant_codes = validated_data.pop('variant_codes', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if variant_codes is not None:
            # 기존 연결 제거 후 다시 추가
            SupplierVariant.objects.filter(supplier=instance).delete()
            variants = ProductVariant.objects.filter(variant_code__in=variant_codes)
            for variant in variants:
                SupplierVariant.objects.create(supplier=instance, variant=variant)

        return instance