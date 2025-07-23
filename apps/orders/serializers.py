from rest_framework import serializers
from apps.orders.models import Order, OrderItem
from apps.inventory.models import ProductVariant
from apps.supplier.models import Supplier
from apps.inventory.serializers import ProductVariantSerializer
from django.contrib.auth import get_user_model


User = get_user_model()
class OrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    variant_code = serializers.CharField(source='variant.variant_code', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'variant_code', 'item_name', 'quantity', 'unit_price', 'remark', 'spec']

    def get_item_name(self, obj):
        return obj.variant.product.name if obj.variant and obj.variant.product else None
# READ 전용
class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    supplier = serializers.CharField(source='supplier.name', read_only=True)
    manager = serializers.CharField(source='manager.first_name', read_only=True)

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

class OrderItemWriteSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(write_only=True)

    class Meta:
        model = OrderItem
        fields = ['variant_code', 'quantity', 'unit_price', 'remark', 'spec']

    def create(self, validated_data):
        variant_code = validated_data.pop('variant_code')
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError({
                "variant_code": f"variant_code '{variant_code}' does not exist."
            })
        return OrderItem(variant=variant, **validated_data)
    

class OrderWriteSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    manager_name = serializers.CharField(write_only=True)

    class Meta:
        model = Order
        fields = [
            'supplier',
            'manager_name',
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
        manager_name = validated_data.pop('manager_name')

        try:
            manager = User.objects.get(first_name=manager_name)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "manager_name": f"'{manager_name}'이라는 이름을 가진 사용자가 존재하지 않습니다."
            })

        order = Order.objects.create(manager=manager, **validated_data)

        for item_data in items_data:
            item = OrderItemWriteSerializer().create(item_data)
            item.order = order
            item.save()

        return order

class OrderCompactSerializer(serializers.ModelSerializer):
    total_quantity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    product_names = serializers.SerializerMethodField()
    supplier = serializers.CharField(source='supplier.name', read_only=True)
    manager = serializers.CharField(source='manager.first_name', read_only=True)
    expected_delivery_date = serializers.DateField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'supplier',
            'manager',
            'status',
            'note',
            'order_date',
            'expected_delivery_date',
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