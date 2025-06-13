from rest_framework import serializers
from apps.orders.models import Order
from apps.inventory.models import ProductVariant
from apps.inventory.serializers import ProductVariantSerializer

class OrderSerializer(serializers.ModelSerializer):
    variant_id = serializers.SlugRelatedField(
        slug_field='variant_code',
        queryset=ProductVariant.objects.all(),
        source='variant'
    )
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'variant_id',
            'variant', 
            'supplier_id',
            'quantity',
            'status',
            'note',       
            'order_date'
        ]
        read_only_fields = ['id', 'order_date']


class OrderCompactSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    variant_code = serializers.CharField(source='variant.variant_code')
    option = serializers.CharField(source='variant.option')
    price = serializers.IntegerField(source='variant.price')

    class Meta:
        model = Order
        fields = [
            'id',
            'variant_code',
            'product_name',
            'option',
            'price',
            'supplier_id',
            'quantity',
            'status',
            'note',
            'order_date',
        ]

    def get_product_name(self, obj):
        return obj.variant.product.name