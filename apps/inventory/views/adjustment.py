# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, generics
from django_filters.rest_framework import DjangoFilterBackend

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Serializer, Model
from ..serializers import (
    InventoryAdjustmentSerializer,
    InventoryAdjustmentCreateSerializer
)

from ..models import (
    InventoryAdjustment,
    ProductVariantStatus
)

from ..filters import InventoryAdjustmentFilter

class InventoryAdjustmentView(generics.ListCreateAPIView):
    """
    재고 조정 관리 API

    GET  /inventory/adjustments/
    - 재고 조정 이력 조회
    - variant_code, year, month 필터 가능
    - 최신순 정렬

    POST /inventory/adjustments/
    - 재고 조정 이력 생성
    - 생성 시 ProductVariantStatus(year, month)에
      stock_adjustment 누적 반영
    """

    permission_classes = [AllowAny]
    queryset = InventoryAdjustment.objects.select_related(
        "variant", "variant__product"
    )
    filterset_class = InventoryAdjustmentFilter
    filter_backends = [DjangoFilterBackend]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InventoryAdjustmentCreateSerializer
        return InventoryAdjustmentSerializer

    # -------------------------
    # GET: 조정 이력 조회
    # -------------------------
    @swagger_auto_schema(
        operation_summary="재고 조정 이력 조회",
        operation_description=(
            "재고 조정 이력을 조회합니다.\n\n"
            "- variant_code, year, month 기준 필터 가능\n"
            "- 최신순 정렬"
        ),
        tags=["inventory - Stock Adjust"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    # -------------------------
    # POST: 조정 등록
    # -------------------------
    @swagger_auto_schema(
        operation_summary="재고 조정 등록",
        operation_description=(
            "재고 조정을 등록합니다.\n\n"
            "처리 흐름:\n"
            "1. InventoryAdjustment 생성 (이력 저장)\n"
            "2. 해당 year/month의 ProductVariantStatus 조회 또는 생성\n"
            "3. stock_adjustment에 delta 누적 반영\n\n"
        ),
        tags=["inventory - Stock Adjust"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["variant_code", "delta", "reason", "created_by"],
            properties={
                "variant_code": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="P00001-A",
                    description="조정 대상 variant_code",
                ),
                "year": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    example=2025,
                    description="조정 연도 (미입력 시 현재 연도)",
                ),
                "month": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    example=12,
                    description="조정 월 (미입력 시 현재 월)",
                ),
                "delta": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    example=-5,
                    description="재고 조정 수량 (음수/양수 가능)",
                ),
                "reason": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="분기 실사 재고 차이",
                    description="조정 사유",
                )
            },
        ),
        responses={201: InventoryAdjustmentSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request} 
        )
        serializer.is_valid(raise_exception=True)
        adjustment = serializer.save()

        # ProductVariantStatus 반영
        ProductVariantStatus.objects.get_or_create(
            year=adjustment.year,
            month=adjustment.month,
            variant=adjustment.variant,
            defaults={
                "product": adjustment.variant.product,
            },
        )

        output_serializer = InventoryAdjustmentSerializer(adjustment)

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
