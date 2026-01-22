# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from django.db import transaction
from django.db.models import Sum

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


# Serializer, Model
from ..serializers import (
   ProductVariantStatusSerializer
)

from ..models import (
    ProductVariant,
    ProductVariantStatus,
    InventoryAdjustment
)

from ..filters import ProductVariantStatusFilter
from rest_framework.pagination import PageNumberPagination

class ProductVariantStatusCreateView(APIView):
    """
    POST /inventory/variant-status/{year}/{month}
    저번 달 재고 기준으로 이번 달 스냅샷 생성
    """

    permission_classes = [AllowAny]
    @swagger_auto_schema(
            operation_summary="저번 달 재고 불러오기 (이번 달 엑셀 생성)",
            operation_description=(
                "저번 달(ProductVariantStatus)을 기준으로\n"
                "이번 달 재고 스냅샷을 자동 생성합니다.\n\n"
                "동작 규칙:\n"
                "- {year}/{month} = 생성할 대상 월\n"
                "- 저번 달 데이터가 없으면 404\n"
                "- 이미 이번 달 데이터가 있으면 스킵\n"
                "- 저번 달 기말재고 → 이번 달 창고 기초재고로 이월\n"
            ),
            manual_parameters=[
                openapi.Parameter(
                    name="year",
                    in_=openapi.IN_PATH,
                    type=openapi.TYPE_INTEGER,
                    required=True,
                    description="생성할 연도 (예: 2026)",
                ),
                openapi.Parameter(
                    name="month",
                    in_=openapi.IN_PATH,
                    type=openapi.TYPE_INTEGER,
                    required=True,
                    description="생성할 월 (1~12)",
                ),
            ],
            responses={
                201: openapi.Response(
                    description="생성 완료",
                    examples={
                        "application/json": {
                            "message": "이번 달 재고 스냅샷 생성 완료",
                            "year": 2026,
                            "month": 2,
                            "created": 120,
                            "skipped": 3,
                        }
                    },
                ),
                400: "잘못된 요청 (year/month 형식 오류)",
                404: "저번 달 데이터 없음",
            },
            tags=["inventory - Variant Status (엑셀 행 하나)"],
        )
    def post(self, request, year: int, month: int):

        # -------- validation --------
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response(
                {"detail": "year, month는 정수여야 합니다."},
                status=400
            )

        if not (1 <= month <= 12):
            return Response(
                {"detail": "month는 1~12 사이여야 합니다."},
                status=400
            )

        # -------- 저번달 계산 --------
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1

        # -------- 저번달 데이터 --------
        prev_status_qs = ProductVariantStatus.objects.select_related(
            "variant", "product"
        ).filter(
            year=prev_year,
            month=prev_month,
        )

        if not prev_status_qs.exists():
            return Response(
                {"detail": "저번 달 재고 데이터가 없습니다."},
                status=404
            )

        created_count = 0
        skipped_count = 0

        with transaction.atomic():

            for prev in prev_status_qs:

                # 이미 이번달 데이터 있으면 skip
                if ProductVariantStatus.objects.filter(
                    year=year,
                    month=month,
                    variant=prev.variant
                ).exists():
                    skipped_count += 1
                    continue

                adjustment_sum = (
                    InventoryAdjustment.objects.filter(
                        variant=prev.variant,
                        year=prev_year,
                        month=prev_month,
                    ).aggregate(total=Sum("delta"))["total"]
                    or 0
                )

                ending_stock = (
                    prev.warehouse_stock_start
                    + prev.store_stock_start
                    + prev.inbound_quantity
                    - (prev.store_sales + prev.online_sales)
                    + adjustment_sum
                )

                # -------- 이번달 생성 --------
                ProductVariantStatus.objects.create(
                    product=prev.product,
                    variant=prev.variant,
                    year=year,
                    month=month,
                    warehouse_stock_start=ending_stock,
                    store_stock_start=0,
                    inbound_quantity=0,
                    store_sales=0,
                    online_sales=0,
                )

                created_count += 1

        return Response(
            {
                "message": "이번 달 재고 스냅샷 생성 완료",
                "year": year,
                "month": month,
                "created": created_count,
                "skipped": skipped_count,
            },
            status=status.HTTP_201_CREATED,
        )

class VariantStatusPagination(PageNumberPagination):
    page_size = 10                 # 기본값
    page_size_query_param = "page_size"
    max_page_size = 200            # 안전장치

class ProductVariantStatusListView(generics.ListAPIView):
    """
    GET: 월별 재고 현황 조회 (year, month 필수)
    """
    permission_classes = [AllowAny]
    serializer_class = ProductVariantStatusSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductVariantStatusFilter
    ordering = ["product__product_id", "variant__variant_code"]
    pagination_class = VariantStatusPagination

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
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="페이지 번호 (default: 1)",
            ),
            openapi.Parameter(
                "page_size",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="페이지당 행 수 (default: 10, max: 200)",
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
    DELETE: 재고 스냅샷 삭제

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
    
    @swagger_auto_schema(
        operation_summary="재고 행 삭제",
        operation_description=(
            "엑셀 화면에서 선택한 한 행(ProductVariantStatus)을 삭제합니다.\n\n"
            "삭제 기준:\n"
            "- year / month / variant_code로 대상 행 식별\n\n"
            "주의:\n"
            "- 삭제된 데이터는 복구할 수 없습니다.\n"
        ),
        manual_parameters=[
            openapi.Parameter(
                name="year",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="연도 (예: 2026)",
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
                description="상품 variant_code (예: P00000FE000A)",
            ),
        ],
        responses={
            200: openapi.Response(
                description="삭제 성공",
                examples={
                    "application/json": {
                        "message": "행 삭제 완료",
                        "variant_code": "P00000FE000A"
                    }
                },
            ),
            404: "존재하지 않는 행",
        },
        tags=["inventory - Variant Status (엑셀 행 하나)"],
    )

    def delete(self, request, year: int, month: int, variant_code: str):

        variant = get_object_or_404(
            ProductVariant,
            variant_code=variant_code,
            is_active=True
        )

        status_obj = get_object_or_404(
            ProductVariantStatus,
            year=year,
            month=month,
            variant=variant
        )

        status_obj.delete()

        return Response(
            {
                "message": "행 삭제 완료",
                "variant_code": variant_code
            },
            status=200
        )
    
class ProductVariantStatusBulkUpdateView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="월별 재고 일괄 저장 (동시 수정 대응)",
        operation_description=(
            "엑셀 화면에서 여러 행을 한 번에 저장하는 벌크 수정 API입니다.\n\n"
            "동시 수정 방지를 위해 Optimistic Lock(version)을 사용합니다.\n\n"
            "동작 방식:\n"
            "1. GET API에서 각 행의 version 값을 받습니다.\n"
            "2. 저장 시 동일한 version 값을 함께 전송해야 합니다.\n"
            "3. 서버 version과 다르면 해당 행은 저장되지 않고 conflicts에 반환됩니다.\n\n"
            "응답 필드:\n"
            "- updated: 정상 저장된 행 수\n"
            "- conflicts: 동시 수정 충돌 발생 행 목록\n"
            "- errors: 잘못된 데이터 행 목록\n"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["year", "month", "rows"],
            properties={
                "year": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    example=2026,
                    description="수정할 연도"
                ),
                "month": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    example=2,
                    description="수정할 월 (1~12)"
                ),
                "rows": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="수정할 행 목록",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        required=["variant_code", "version"],
                        properties={
                            "variant_code": openapi.Schema(
                                type=openapi.TYPE_STRING,
                                example="P00001-A",
                                description="상품 옵션 코드"
                            ),
                            "version": openapi.Schema(
                                type=openapi.TYPE_INTEGER,
                                example=3,
                                description="GET API에서 받은 version 값"
                            ),
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
                    ),
                ),
            },
            example={
                "year": 2026,
                "month": 2,
                "rows": [
                    {
                        "variant_code": "P00001-A",
                        "warehouse_stock_start": 120,
                        "store_sales": 20,
                        "version": 0
                    },
                    {
                        "variant_code": "P00002-A",
                        "inbound_quantity": 50,
                        "version": 1
                    }
                ]
            },
        ),
        responses={
            200: openapi.Response(
                description="벌크 저장 결과",
                examples={
                    "application/json": {
                        "message": "벌크 저장 완료",
                        "updated": 1,
                        "conflicts": [
                            {
                                "variant_code": "P00000FE000B",
                                "server_version": 2,
                                "client_version": 1
                            }
                        ],
                        "errors": []
                    }
                }
            ),
            400: "잘못된 요청 (필수 파라미터 누락)",
        },
        tags=["inventory - Variant Status (엑셀 전체 대응)"],
    )

    def patch(self, request):

        year = request.data.get("year")
        month = request.data.get("month")
        rows = request.data.get("rows", [])

        if not year or not month or not rows:
            return Response(
                {"detail": "year, month, rows 필수"},
                status=400
            )

        allowed = {
            "warehouse_stock_start",
            "store_stock_start",
            "inbound_quantity",
            "store_sales",
            "online_sales"
        }

        updated = 0
        conflicts = []
        errors = []

        with transaction.atomic():

            for row in rows:

                variant_code = row.get("variant_code")
                client_version = row.get("version")

                if not variant_code:
                    continue

                # 1. Variant 조회
                try:
                    variant = ProductVariant.objects.get(
                        variant_code=variant_code,
                        is_active=True
                    )
                except ProductVariant.DoesNotExist:
                    errors.append({
                        "variant_code": variant_code,
                        "error": "존재하지 않는 variant"
                    })
                    continue

                # 2. Status 조회
                try:
                    status_obj = ProductVariantStatus.objects.get(
                        year=year,
                        month=month,
                        variant=variant
                    )
                except ProductVariantStatus.DoesNotExist:
                    errors.append({
                        "variant_code": variant_code,
                        "error": "해당 월 재고 데이터 없음"
                    })
                    continue

                # 3. version 충돌 체크
                if client_version != status_obj.version:
                    conflicts.append({
                        "variant_code": variant_code,
                        "server_version": status_obj.version,
                        "client_version": client_version,
                    })
                    continue

                # 4. 실제 업데이트
                dirty = []

                for k, v in row.items():
                    if k in allowed:
                        setattr(status_obj, k, v)
                        dirty.append(k)

                if dirty:
                    status_obj.version += 1
                    dirty.append("version")

                    status_obj.save(update_fields=dirty)
                    updated += 1

        return Response(
            {
                "message": "벌크 저장 완료",
                "updated": updated,
                "conflicts": conflicts,
                "errors": errors
            }
        )
