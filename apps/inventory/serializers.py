from rest_framework import serializers
from .models import InventoryItem, ProductVariant


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
