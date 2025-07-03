from rest_framework import serializers
from apps.orders.models import Order, OrderItem
from apps.inventory.models import ProductVariant
from apps.supplier.models import Supplier
from apps.inventory.serializers import ProductVariantSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        fields = ['id', 'variant', 'item_name', 'quantity', 'unit_price', 'remark', 'spec']

    def get_item_name(self, obj):
        return obj.variant.product.name if obj.variant and obj.variant.product else None

# READ 전용
class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    supplier = serializers.CharField(source='supplier.name', read_only=True)
    manager = serializers.CharField(source='manager.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'supplier',
            'manager',
            'order_date',
            'expected_delivery_date',
            'status',
            'instruction_note',
            'note',
            'created_at',
            'vat_included',
            'packaging_included',
            'items'
        ]

# POST / PUT 용
class OrderWriteSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())

    class Meta:
        model = Order
        fields = [
            'supplier',
            'order_date',
            'expected_delivery_date',
            'status',
            'instruction_note',
            'note',
            'vat_included',
            'packaging_included',
            'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item in items_data:
            OrderItem.objects.create(order=order, **item)
        return order


class OrderCompactSerializer(serializers.ModelSerializer):
    total_quantity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    product_names = serializers.SerializerMethodField()
    supplier = serializers.CharField(source='supplier.name', read_only=True)
    manager = serializers.CharField(source='manager.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'supplier',
            'manager',
            'status',
            'note',
            'order_date',
            'total_quantity',
            'total_price',
            'product_names'
        ]

    def get_total_quantity(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj):
        return sum(item.quantity * item.unit_price for item in obj.items.all())

    def get_product_names(self, obj):
        names = set()
        for item in obj.items.all():
            if item.variant and item.variant.product:
                names.add(item.variant.product.name)
        return list(names)