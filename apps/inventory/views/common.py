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
    InventoryItemSummarySerializer,
    ProductSimpleSerializer,
    ProductCategorySerializer
)

from ..models import (
    InventoryItem,
    ProductVariant
)

# 빠른 값 조회용 엔드포인트
class ProductOptionListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 옵션 리스트 조회",
        operation_description=(
            "드롭다운용 상품 옵션 리스트를 반환합니다.\n"
            "표시명: 상품명 (option, detail_option)"
        ),
        responses={200: InventoryItemSummarySerializer(many=True)},
        tags=["inventory - View"],
    )
    def get(self, request):
        variants = (
            ProductVariant.objects
            .filter(is_active=True)
            .select_related("product")
            .only(
                "id",
                "variant_code",
                "option",
                "detail_option",
                "product__name",
            )
            .order_by("product__name", "variant_code")
        )

        serializer = InventoryItemSummarySerializer(variants, many=True)
        return Response(serializer.data)

class InventoryCategoryListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="카테고리 목록 조회",
        operation_description=(
            "InventoryItem에 등록된 카테고리 관련 필드들의 "
            "고유 목록을 반환합니다.\n\n"
            "- big_category\n"
            "- middle_category\n"
            "- category"
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "big_categories": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(type=openapi.TYPE_STRING),
                        example=["STORE", "ONLINE"],
                    ),
                    "middle_categories": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(type=openapi.TYPE_STRING),
                        example=["FASHION", "BOOK"],
                    ),
                    "categories": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(type=openapi.TYPE_STRING),
                        example=["문구", "의류"],
                    ),
                },
            )
        },
        tags=["inventory - View"],
    )
    def get(self, request):
        qs = InventoryItem.objects.all()

        big = qs.values_list("big_category", flat=True)
        middle = qs.values_list("middle_category", flat=True)
        category = qs.values_list("category", flat=True)

        def uniq(values):
            return sorted({v.strip() for v in values if v})

        return Response(
            {
                "big_categories": uniq(big),
                "middle_categories": uniq(middle),
                "categories": uniq(category),
            },
            status=status.HTTP_200_OK,
        )

class ProductListSimpleView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 목록 조회",
        operation_description="product_id, name, online_name 반환",
        responses={200: ProductSimpleSerializer(many=True)},
        tags=["inventory - View"]
    )
    def get(self, request):

        qs = InventoryItem.objects.filter(is_active=True)

        serializer = ProductSimpleSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ProductCategoryView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 카테고리 조회",
        operation_description="해당 상품의 카테고리 정보 반환",
        manual_parameters=[
            openapi.Parameter(
                "product_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: ProductCategorySerializer},
        tags=["inventory - View"]
    )
    def get(self, request, product_id):

        try:
            product = InventoryItem.objects.get(
                product_id=product_id,
                is_active=True
            )
        except InventoryItem.DoesNotExist:
            return Response(
                {"detail": "존재하지 않는 상품입니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductCategorySerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
