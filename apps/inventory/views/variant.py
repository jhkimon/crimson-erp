# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Serializer, Model
from ..serializers import (
    ProductVariantSerializer,
    ProductVariantWriteSerializer
)

from ..models import (
    InventoryItem,
    ProductVariant
)

from ..filters import ProductVariantFilter
from ..utils.variant_code import generate_variant_code

# 상품 상세 정보 관련 View
class ProductVariantView(APIView):
    """
    POST : 상품 상세 추가
    GET : 쿼리 파라미터 기반 Product Variant 조회
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductVariantFilter
    ordering_fields = ["stock", "price"]

    @swagger_auto_schema(
        operation_summary="상품 상세 정보 생성",
        tags=["inventory - Variant CRUD"],
        operation_description=(
            "상품 상세(SKU) 생성 API\n\n"
            "- product_id 기준으로 상품(InventoryItem)을 조회/생성\n"
            "- Product 필드와 Variant 필드를 동시에 입력 가능\n"
            "- 옵션/상세옵션 기반으로 variant_code(SKU)는 자동 생성됨"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["product_id", "name"],
            properties={
                # ===== Product =====
                "product_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="상품 식별자 (Product ID)",
                    example="P00000YC",
                ),
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="오프라인 상품명",
                    example="방패 필통",
                ),
                "online_name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="온라인 상품명",
                    example="방패 필통 온라인",
                ),
                "category": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="카테고리",
                    example="문구",
                ),
                "big_category": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="대분류",
                    example="STORE",
                ),
                "middle_category": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="중분류",
                    example="FASHION",
                ),

                # ===== Variant =====
                "option": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="옵션 (예: 색상)",
                    example="화이트",
                ),
                "detail_option": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="상세 옵션 (예: 사이즈)",
                    example="M",
                ),
                "stock": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="초기 재고 (기말 재고)",
                    example=100,
                ),
                "price": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="판매가",
                    example=5900,
                ),
                "min_stock": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="최소 재고 알림 기준",
                    example=5,
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="상품 설명",
                    example="튼튼한 방패 필통",
                ),
                "memo": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="메모",
                    example="23FW 신상품",
                ),
                "channels": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="판매 채널",
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    example=["online", "offline"],
                ),
            },
            example={
                "product_id": "P00000YC",
                "name": "방패 필통",
                "online_name": "방패 필통 온라인",
                "big_category": "STORE",
                "middle_category": "FASHION",
                "category": "문구",
                "option": "화이트",
                "detail_option": "M",
                "stock": 100,
                "price": 5900,
                "min_stock": 5,
                "description": "튼튼한 방패 필통",
                "memo": "23FW 신상품",
                "channels": ["online", "offline"],
            },
        ),
        responses={
            201: ProductVariantSerializer,
            400: "Bad Request",
        },
    )
    def post(self, request):
        product_id = request.data.get("product_id")
        product_name = request.data.get("name")

        if not product_id or not product_name:
            return Response(
                {"error": "product_id와 name은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product, created = InventoryItem.objects.get_or_create(
            product_id=product_id, defaults={"name": product_name}
        )

        if not created:
            product.name = product_name
            product.save()

        serializer = ProductVariantWriteSerializer(
            data=request.data, context={"product": product, "request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                ProductVariantSerializer(serializer.instance).data,
                status=201
            )


        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="상품 상세 목록 조회",
        tags=["inventory - View"],
        manual_parameters=[
            openapi.Parameter(
                "stock_lt",
                openapi.IN_QUERY,
                description="재고 수량 미만",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "stock_gt",
                openapi.IN_QUERY,
                description="재고 수량 초과",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "sales_min",
                openapi.IN_QUERY,
                description="최소 매출",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "sales_max",
                openapi.IN_QUERY,
                description="최대 매출",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="페이지 번호 (default = 1)",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "ordering",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="정렬 필드 (-price, stock 등)",
            ),
            openapi.Parameter(
                "product_name",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="상품명 검색 (부분일치)",
            ),
            openapi.Parameter(
                "category",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="상품 카테고리 (부분일치)",
            ),
            openapi.Parameter(
                "channel",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="채널 필터 (online/offline)",
            ),
        ],
        responses={200: ProductVariantSerializer(many=True)},
    )
    def get(self, request):
        queryset = ProductVariant.objects.select_related("product").all()

        # filtering
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, self)

        # pagination (고정 page_size = 10)
        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(queryset, request, view=self)

        serializer = ProductVariantSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProductVariantDetailView(APIView):
    """
    GET / PATCH / DELETE: 특정 상품의 상세 정보 접근
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 조회 (방패필통 크림슨)",
        tags=["inventory - View"],
        manual_parameters=[
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                description="조회할 variant_code (예: P00000XN000A)",
                type=openapi.TYPE_STRING,
            )
        ],
        responses={200: ProductVariantSerializer, 404: "Not Found"},
    )
    def get(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.filter(
                variant_code=variant_code, is_active=True
            ).first()
            if not variant:
                return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 수정 (방패필통 크림슨)",
        tags=["inventory - Variant CRUD"],
        manual_parameters=[
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                description="수정할 variant_code (예: P00000YC000A)",
                type=openapi.TYPE_STRING,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["product_id", "name", "option", "stock", "price"],
            properties={
                "product_id": openapi.Schema(
                    type=openapi.TYPE_STRING, example="P00000YC"
                ),
                "name": openapi.Schema(type=openapi.TYPE_STRING, example="방패 필통"),
                "option": openapi.Schema(
                    type=openapi.TYPE_STRING, example="색상 : 크림슨"
                ),
                "price": openapi.Schema(type=openapi.TYPE_INTEGER, example=5000),
                "min_stock": openapi.Schema(type=openapi.TYPE_INTEGER, example=4),
                "description": openapi.Schema(type=openapi.TYPE_STRING, example=""),
                "memo": openapi.Schema(type=openapi.TYPE_STRING, example=""),
            },
        ),
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"},
    )
    def patch(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantWriteSerializer(
            variant,
            data=request.data,
            partial=True,
            context={
                "request": request,
                "product": variant.product,
            },
        )

        if serializer.is_valid():
            serializer.save()
            return Response(ProductVariantSerializer(serializer.instance).data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 삭제 (방패필통 크림슨)",
        tags=["inventory - Variant CRUD"],
        manual_parameters=[
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                description="삭제할 variant_code (예: P00000XN000A)",
                type=openapi.TYPE_STRING,
            )
        ],
        responses={204: "삭제 완료", 404: "Not Found"},
    )
    def delete(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

