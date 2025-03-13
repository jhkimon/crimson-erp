from rest_framework import serializers
from .models import InventoryItem, ProductVariant


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class ProductVariantSerializer(serializers.ModelSerializer):

    inventory_item = InventoryItemSerializer(read_only=True)
    inventory_item_id = serializers.PrimaryKeyRelatedField(
        queryset=InventoryItem.objects.all(),
        source='inventory_item',
        write_only=True
    )

    class Meta:
        model = ProductVariant
        fields = [
            'id',                   # variant_id
            'inventory_item',       # 품목명 및 품목코드
            'inventory_item_id',    # product_id
            'variant_code',         # variant_code
            'option',               # 옵션
            'stock',                # 재고량
            'price',                # 가격
            'created_at',           # 생성일시
            'updated_at'            # 수정일시
        ]
        read_only_fields = ['id', 'created_at']
