from django.db import models
from django.db.models import Sum, F, Q

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from ..models import ProductVariantStatus
from ..serializers import ProductVariantStatusSerializer
from ..filters import ProductVariantStatusFilter

class ProductVariantExportView(APIView):
    """
    엑셀 다운로드용 Export API
    기준: ProductVariantStatus (월별 재고 스냅샷)
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductVariantStatusFilter

    @swagger_auto_schema(
        operation_summary="상품 재고 현황 Export (엑셀용)",
        operation_description=(
            "월별 ProductVariantStatus 기준으로\n"
            "상품 / 옵션 / 재고 / 판매 / 재고조정 정보를 한 행으로 반환합니다.\n\n"
            "엑셀 다운로드 및 관리 화면 테이블 출력 용도입니다."
        ),
        tags=["inventory - Export"],
        manual_parameters=[
            openapi.Parameter(
                "year",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="조회 연도 (예: 2025)",
                required=True,
            ),
            openapi.Parameter(
                "month",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="조회 월 (1~12)",
                required=True,
            ),
            openapi.Parameter(
                "product_code",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="상품 코드 검색 (product_id, 부분 일치)",
            ),
            openapi.Parameter(
                "variant_code",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="상품 상세 코드 검색 (variant_code, 부분 일치)",
            ),
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="카테고리 필터 (부분 일치)",
            ),
        ],
        responses={200: ProductVariantStatusSerializer(many=True)},
    )
    
    def get(self, request):
        queryset = (
            ProductVariantStatus.objects
            .select_related("product", "variant")
            .annotate(
                adjustment_total=Sum(
                    "variant__adjustments__delta",
                    filter=Q(
                        variant__adjustments__year=F("year"),
                        variant__adjustments__month=F("month"),
                    ),
                )
            )
        )

        # filtering
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, self)

        serializer = ProductVariantStatusSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
