# apps/orders/serializers.py
from rest_framework import serializers
from .models import Order
from apps.inventory.models import InventoryItem
from apps.inventory.serializers import InventoryItemSerializer
from apps.inventory.models import ProductVariant

class OrderSerializer(serializers.ModelSerializer):
    variant = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'variant_id',
            'variant',
            'supplier_id',
            'quantity',
            'status',
            'order_date'
        ]
        read_only_fields = ['id', 'order_date']

    def get_variant(self, obj):
        try:
            # 1. variant_code로 ProductVariant 찾기
            variant = ProductVariant.objects.get(variant_code=obj.variant_id)
            
            # 2. 그 안에 연결된 InventoryItem (variant.product)
            item = variant.product

            # 3. InventoryItem 직렬화해서 반환
            return InventoryItemSerializer(item).data

        except ProductVariant.DoesNotExist:
            return None