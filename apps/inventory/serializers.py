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
        fields = '__all__'
