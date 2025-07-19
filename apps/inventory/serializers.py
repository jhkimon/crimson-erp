from rest_framework import serializers
from .models import InventoryItem, ProductVariant, InventoryAdjustment, SalesChannel, SalesTransaction, SalesTransactionItem, StockReservation


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class ProductVariantSerializer(serializers.ModelSerializer):

    inventory_item = InventoryItemSerializer(source='product', read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=InventoryItem.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = ProductVariant
        fields = [
            'id',                   # variant_id
            'inventory_item',       # 품목명 및 품목코드
            'product_id',    # product_id
            'variant_code',         # variant_code
            'option',               # 옵션
            'stock',                # 재고량
            'price',                # 가격
            'created_at',           # 생성일시
            'updated_at'            # 수정일시
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    # 수정 시 기본 정보(inventory_item)는 가져오지 않기

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        # POST, PUT, PATCH 요청 시에는 기본 정보 필드 입력 제거거
        if request and request.method in ['POST', 'PUT', 'PATCH']:
            fields.pop('inventory_item', None)
            fields.pop('product_id', None)
        return fields

    def create(self, validated_data):
        # POST 요청 시, 외래키(Product)는 get_fields()에서 제거되어 validated_data에 포함되어 있지 않습니다.
        # 대신 뷰에서 전달한 context에서 InventoryItem 객체를 가져와 넣어줍니다.
        product = self.context.get('product')
        if product:
            validated_data['product'] = product
        return ProductVariant.objects.create(**validated_data)


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        source='variant',
        write_only=True
    )
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = [
            'id', 'variant', 'variant_id', 'delta', 'reason', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'variant']


class SalesChannelSerializer(serializers.ModelSerializer):
    channel_type_display = serializers.CharField(
        source='get_channel_type_display', read_only=True)

    class Meta:
        model = SalesChannel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display',
            'api_key', 'webhook_url', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'api_key': {'write_only': True}  # 보안을 위해 읽기 시 숨김
        }


class SalesTransactionItemSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(
        source='variant.variant_code', read_only=True)
    variant_option = serializers.CharField(
        source='variant.option', read_only=True)
    product_name = serializers.CharField(
        source='variant.product.name', read_only=True)

    class Meta:
        model = SalesTransactionItem
        fields = [
            'id', 'variant', 'variant_code', 'variant_option', 'product_name',
            'quantity', 'unit_price', 'total_price',
            'is_stock_reserved', 'is_stock_deducted', 'created_at'
        ]
        read_only_fields = ['created_at', 'total_price']


class SalesTransactionSerializer(serializers.ModelSerializer):
    items = SalesTransactionItemSerializer(many=True, read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(
        source='channel.channel_type', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

    class Meta:
        model = SalesTransaction
        fields = [
            'id', 'external_order_id', 'channel', 'channel_name', 'channel_type',
            'status', 'status_display', 'customer_name', 'customer_phone',
            'total_amount', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockReservationSerializer(serializers.ModelSerializer):
    variant_code = serializers.CharField(
        source='variant.variant_code', read_only=True)
    variant_option = serializers.CharField(
        source='variant.option', read_only=True)
    transaction_order_id = serializers.CharField(
        source='transaction_item.transaction.external_order_id', read_only=True)

    class Meta:
        model = StockReservation
        fields = [
            'id', 'variant', 'variant_code', 'variant_option',
            'transaction_item', 'transaction_order_id',
            'reserved_quantity', 'expires_at', 'is_confirmed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# 온라인 POS 연동용 특별 시리얼라이저들

class OnlinePOSOrderItemSerializer(serializers.Serializer):
    """온라인 POS에서 받을 주문 상품 데이터"""
    variant_code = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.IntegerField(min_value=0)


class OnlinePOSOrderSerializer(serializers.Serializer):
    """온라인 POS에서 받을 주문 데이터"""
    external_order_id = serializers.CharField(max_length=100)
    channel_api_key = serializers.CharField(max_length=255)
    customer_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True)
    customer_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True)
    items = OnlinePOSOrderItemSerializer(many=True)

    def validate_items(self, value):
        """주문 상품이 비어있지 않은지 확인"""
        if not value:
            raise serializers.ValidationError("주문 상품이 비어있습니다.")
        return value


class StockCheckSerializer(serializers.Serializer):
    """재고 확인용 시리얼라이저"""
    variant_code = serializers.CharField(max_length=50)
    requested_quantity = serializers.IntegerField(min_value=1)


class BulkStockCheckSerializer(serializers.Serializer):
    """대량 재고 확인용 시리얼라이저"""
    items = StockCheckSerializer(many=True)


# 간단한 응답용 시리얼라이저들
class SimpleProductVariantSerializer(serializers.ModelSerializer):
    """간단한 상품 변형 정보만 반환"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    available_stock = serializers.ReadOnlyField()

    class Meta:
        model = ProductVariant
        fields = ['variant_code', 'option',
                  'product_name', 'price', 'available_stock']


class StockStatusSerializer(serializers.Serializer):
    """재고 상태 응답용"""
    variant_code = serializers.CharField()
    available = serializers.BooleanField()
    available_stock = serializers.IntegerField()
    message = serializers.CharField(required=False)
