# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Serializer, Model
from ..serializers import (
    InventoryItemSummarySerializer
)

from ..models import (
    InventoryItem
)


# 빠른 값 조회용 엔드포인트
class ProductOptionListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 옵션 리스트 조회",
        operation_description="상품 드롭다운용으로 product_id와 name만 간단히 반환합니다.",
        responses={200: InventoryItemSummarySerializer(many=True)},
        tags=["inventory - View"],
    )
    def get(self, request):
        products = InventoryItem.objects.all().only("product_id", "name")
        serializer = InventoryItemSummarySerializer(products, many=True)
        return Response(serializer.data)


class InventoryCategoryListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="카테고리 목록 조회",
        operation_description="InventoryItem에 등록된 카테고리 문자열의 고유 목록을 반환합니다.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING),
                description="카테고리 이름 리스트",
                example=["문구", "도서", "의류"],
            )
        },
        tags=["inventory - View"],
    )
    def get(self, request):
        raw = InventoryItem.objects.values_list("category", flat=True)
        names = sorted(set(c.strip() for c in raw if c))
        return Response(list(names), status=status.HTTP_200_OK)

