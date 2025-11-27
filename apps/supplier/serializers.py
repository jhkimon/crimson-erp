from rest_framework import serializers
from apps.supplier.models import Supplier
from apps.orders.models import Order, OrderItem


# 빠른 검색용
class SupplierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact', 'manager', 'email', 'address']

# Supplier 전체
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact', 'manager', 'email', 'address'
        ]

    def create(self, validated_data):
        supplier = Supplier.objects.create(**validated_data)
        return supplier

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
    
class SupplierOrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    variant_code = serializers.CharField(source="variant.variant_code", read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["variant_code", "item_name", "quantity", "unit_price", "total"]

    def get_item_name(self, obj):
        if obj.variant and obj.variant.product:
            return obj.variant.product.name
        return None

    def get_total(self, obj):
        return obj.quantity * obj.unit_price


class SupplierOrderSerializer(serializers.ModelSerializer):
    items = SupplierOrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_date",
            "expected_delivery_date",
            "status",
            "total_price",
            "items",
        ]

    def get_total_price(self, obj):
        return sum(item.quantity * item.unit_price for item in obj.items.all())