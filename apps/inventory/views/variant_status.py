# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


# Serializer, Model
from ..serializers import (
   ProductVariantStatusSerializer
)

from ..models import (
    ProductVariant,
    ProductVariantStatus
)

from ..filters import ProductVariantStatusFilter


class ProductVariantStatusListView(generics.ListAPIView):
    """
    GET: 월별 재고 현황 조회 (year, month 필수)
    """
    permission_classes = [AllowAny]
    serializer_class = ProductVariantStatusSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductVariantStatusFilter
    ordering = ["product__product_id", "variant__variant_code"]

    @swagger_auto_schema(
        operation_summary="재고 현황 확인",
        manual_parameters=[
            openapi.Parameter(
                "year", openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="조회 연도 (예: 2025)"
            ),
            openapi.Parameter(
                "month", openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="조회 월 (1~12)"
            ),
        ],
        tags=["inventory - Variant Status (엑셀 행 하나)"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

        # ✅ 필수 파라미터
        if not year or not month:
            raise ValidationError(
                {"detail": "year, month 쿼리 파라미터는 필수입니다."}
            )

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            raise ValidationError(
                {"detail": "year와 month는 정수여야 합니다."}
            )

        if not (1 <= month <= 12):
            raise ValidationError(
                {"detail": "month는 1~12 사이여야 합니다."}
            )

        return ProductVariantStatus.objects.select_related(
            "product", "variant"
        ).filter(
            year=year,
            month=month,
        )
    
class ProductVariantStatusDetailView(APIView):
    """
    PATCH: 월별 재고 스냅샷(ProductVariantStatus) 수동 수정

    PATCH /inventory/variant-status/{year}/{month}/{variant_code}/

    수정 가능 필드:
    - warehouse_stock_start
    - store_stock_start
    - inbound_quantity
    - store_sales
    - online_sales
    """
    

    permission_classes = [AllowAny]

    # PATCH 허용 필드 명시적 제한
    ALLOWED_FIELDS = {
        "warehouse_stock_start",
        "store_stock_start",
        "inbound_quantity",
        "store_sales",
        "online_sales"
    }


    @swagger_auto_schema(
        operation_summary="월별 재고 현황 수정 (셀 단위)",
        operation_description=(
            "엑셀 화면에서 관리자 수동 수정용 PATCH API\n\n"
            "- year / month / variant_code로 대상 식별\n"
            "- 월초재고, 입고, 판매량만 수정 가능\n"
        ),
        manual_parameters=[
            openapi.Parameter(
                name="year",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="연도 (예: 2025)",
            ),
            openapi.Parameter(
                name="month",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="월 (1~12)",
            ),
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="상품 variant_code (예: P00000YC000A)",
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "warehouse_stock_start": openapi.Schema(
                    type=openapi.TYPE_INTEGER, example=120
                ),
                "store_stock_start": openapi.Schema(
                    type=openapi.TYPE_INTEGER, example=30
                ),
                "inbound_quantity": openapi.Schema(
                    type=openapi.TYPE_INTEGER, example=50
                ),
                "store_sales": openapi.Schema(
                    type=openapi.TYPE_INTEGER, example=20
                ),
                "online_sales": openapi.Schema(
                    type=openapi.TYPE_INTEGER, example=10
                ),
            },
            example={
                "inbound_quantity": 40,
                "store_sales": 18,
                "online_sales": 12,
            },
        ),
        responses={
            200: ProductVariantStatusSerializer,
            400: "Invalid field",
            404: "Not Found",
        },
        tags=["inventory - Variant Status (엑셀 행 하나)"],
    )

    def patch(self, request, year: int, month: int, variant_code: str):
        # Variant 조회
        variant = get_object_or_404(
            ProductVariant,
            variant_code=variant_code,
            is_active=True,
        )

        # 해당 월 ProductVariantStatus 조회
        status_obj = get_object_or_404(
            ProductVariantStatus,
            year=year,
            month=month,
            variant=variant,
        )

        # 필드 정리
        update_data = {
            key: value
            for key, value in request.data.items()
            if key in self.ALLOWED_FIELDS
        }

        if not update_data:
            return Response(
                {
                    "error": "수정 가능한 필드가 없습니다.",
                    "allowed_fields": sorted(self.ALLOWED_FIELDS),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field, value in update_data.items():
            setattr(status_obj, field, value)

        status_obj.save(update_fields=list(update_data.keys()))

        serializer = ProductVariantStatusSerializer(status_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)