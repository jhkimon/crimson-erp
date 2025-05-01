from rest_framework import serializers
from .models import Order

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    variant_id = serializers.CharField(required=True)
    supplier_id = serializers.IntegerField(required=True)  # Ensure this is a string
    quantity = serializers.IntegerField(required=True)  # Ensure this is an integer
    status = serializers.CharField(required=True)
    order_date = serializers.DateTimeField(read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'variant_id', 'supplier_id', 'quantity', 'status', 'order_date']
        read_only_fields = ['id', 'order_date']
        extra_kwargs = {
            'variant_id': {'required': True},
            'supplier_id': {'required': True},
            'quantity': {'required': True},
            'status': {'required': True}
        }


    def validate_quantity(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError("quantity는 정수여야 합니다.")
        return value