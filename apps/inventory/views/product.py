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
    InventoryItemWithVariantsSerializer
)

from ..models import (
    InventoryItem
)


# 일부 조회 (Product ID 기준)
class InventoryItemView(APIView):
    """
    GET: 특정 상품 기본 정보 조회 (상품코드, 상품명, 생성일자)
    """

    permission_classes = [AllowAny]

    # 상품 기본 정보 조회
    @swagger_auto_schema(
        operation_summary="특정 상품 상세 정보 조회 (방패필통)",
        operation_description="product_id에 해당하는 상품의 기본 정보와 연결된 상세 상품 목록까지 함께 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="조회할 상품의 product_id (예: P00000YC)",
                type=openapi.TYPE_STRING,
            )
        ],
        responses={200: InventoryItemWithVariantsSerializer, 404: "Not Found"},
    )
    def get(self, request, product_id: str):
        try:
            item = InventoryItem.objects.get(product_id=product_id)
        except InventoryItem.DoesNotExist:
            return Response(
                {"error": "기본 정보가 존재하지 않습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = InventoryItemWithVariantsSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)