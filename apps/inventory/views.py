import io
from datetime import timedelta

import pandas as pd
import openpyxl, xlrd
import os, uuid, json
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils import timezone

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError


from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    InventoryItem,
    ProductVariant,
    InventoryAdjustment,
    ProductVariantStatus
)
from .serializers import (
    InventoryItemSummarySerializer,
    ProductVariantSerializer,
    ProductVariantWriteSerializer,
    InventoryItemWithVariantsSerializer,
    InventoryAdjustmentSerializer,
    ProductVariantStatusSerializer,
    InventoryAdjustmentCreateSerializer
)

from .filters import ProductVariantFilter, InventoryAdjustmentFilter, ProductVariantStatusFilter


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

# 상품 상세 정보 관련 View
class ProductVariantView(APIView):
    """
    POST : 상품 상세 추가
    GET : 쿼리 파라미터 기반 Product Variant 조회
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProductVariantFilter
    ordering_fields = ["stock", "price"]

    def generate_variant_code(self, base_code):
        existing_codes = ProductVariant.objects.filter(
            variant_code__startswith=base_code
        ).values_list("variant_code", flat=True)

        suffix_char = ord("A")
        while True:
            candidate = f"{base_code}000{chr(suffix_char)}"
            if candidate not in existing_codes:
                return candidate
            suffix_char += 1

    @swagger_auto_schema(
        operation_summary="상품 상세 정보 생성 (방패 필통 크림슨)",
        tags=["inventory - Variant CRUD"],
        operation_description=(
            "기존 product_id가 있으면 연결하고, 없으면 새로 생성한 뒤 variant_code 자동 생성"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["product_id", "name"],
            properties={
                "product_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="상품 식별자",
                    example="P00000YC",
                ),
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="상품명", example="방패 필통"
                ),
                "category": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="상품 카테고리",
                    example="문구",
                ),
                "option": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="옵션",
                    example="색상 : 크림슨",
                ),
                "stock": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="초기 재고", example=100
                ),
                "price": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="판매가", example=5900
                ),
                "min_stock": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="최소 재고", example=5
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="설명",
                    example="튼튼한 크림슨 컬러 방패 필통",
                ),
                "memo": openapi.Schema(
                    type=openapi.TYPE_STRING, description="메모", example="23FW 신상품"
                ),
                "channels": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="판매 채널 태그",
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    example=["online", "offline"],
                ),
            },
            example={
                "product_id": "P00000YC",
                "name": "방패 필통",
                "category": "문구",
                "option": "색상 : 크림슨",
                "stock": 100,
                "price": 5900,
                "min_stock": 5,
                "description": "튼튼한 크림슨 컬러 방패 필통",
                "memo": "23FW 신상품",
                "channels": ["online", "offline"],
            },
        ),
        responses={201: ProductVariantSerializer, 400: "Bad Request"},
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

        variant_code = self.generate_variant_code(product.product_id)

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
            variant, data=request.data, context={"request": request}
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


class ProductVariantExportView(APIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProductVariantFilter
    ordering_fields = ["stock", "price"]

    @swagger_auto_schema(
        operation_summary="전체 상품 상세 정보 Export (엑셀용)",
        tags=["inventory - View"],
        manual_parameters=[
            openapi.Parameter("stock_lt", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("stock_gt", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("sales_min", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("sales_max", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                "product_name", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "category", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING
            ),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING),
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

        # ordering
        ordering = request.query_params.get("ordering")
        if ordering:
            queryset = queryset.order_by(ordering)

        serializer = ProductVariantSerializer(queryset, many=True)
        return Response(serializer.data, status=200)

class ProductVariantExcelUploadView(APIView):
    """
    POST: 재고 관리 엑셀 업로드
    - 상품코드 = variant_code
    - 월 단위(ProductVariantStatus) 재고 스냅샷 생성
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="상품 재고 엑셀 업로드",
        tags=["inventory"],
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter(
                name="file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 엑셀 파일 (.xlsx)",
            ),
            openapi.Parameter(
                name="year",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="재고 기준 연도 (default: 현재 연도)",
            ),
            openapi.Parameter(
                name="month",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="재고 기준 월 (default: 현재 월)",
            ),
        ],
    )
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "file is required"}, status=400)

        # ✅ 기준 연/월
        year = int(
            request.query_params.get(
                "year", 
                request.data.get("year", timezone.now().year)
            )
        )
        month = int(
            request.query_params.get(
                "month", 
                request.data.get("month", timezone.now().month)
            )
        )
        print(">>> upload year/month =", year, month)


        # ✅ 엑셀 로딩
        try:
            df = pd.read_excel(file, header=2)
            df.columns = (
                df.columns
                .str.replace("\n", " ", regex=False)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
        except Exception as e:
            return Response({"error": f"엑셀 로드 실패: {str(e)}"}, status=400)

        # ✅ 필수 컬럼
        REQUIRED_COLUMNS = [
            "상품코드",
            "오프라인 품목명",
            "온라인 품목명",
            "옵션",
            "기말 재고",
            "월초창고 재고",
            "월초매장 재고",
            "당월입고물량",
            "매장 판매물량",
            "쇼핑몰 판매물량",
        ]

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            return Response(
                {"error": f"필수 컬럼 누락: {missing_cols}"},
                status=400,
            )

        created_variants = 0
        skipped_variants = 0
        created_status = 0
        errors = []

        def safe_str(row, col):
            val = row.get(col)
            if pd.isna(val):
                return ""
            return str(val).strip()

        def safe_int(row, col):
            val = row.get(col, 0)
            if pd.isna(val) or val == "":
                return 0
            return int(val)

        for idx, row in df.iterrows():
            row_num = idx + 3  # header=2 기준

            try:
                variant_code = safe_str(row, "상품코드")
                if not variant_code:
                    errors.append(f"Row {row_num}: 상품코드 없음")
                    continue

                # ✅ product_id / detail_option
                if "-" in variant_code:
                    product_id, detail_option = variant_code.rsplit("-", 1)
                else:
                    product_id = variant_code
                    detail_option = ""

                offline_name = safe_str(row, "오프라인 품목명")
                online_name = safe_str(row, "온라인 품목명")
                option = safe_str(row, "옵션")

                if not option:
                    errors.append(f"Row {row_num}: 옵션 없음")
                    continue

                # ✅ 숫자 필드
                warehouse_start = safe_int(row, "월초창고 재고")
                store_start = safe_int(row, "월초매장 재고")
                inbound = safe_int(row, "당월입고물량")
                store_sales = safe_int(row, "매장 판매물량")
                online_sales = safe_int(row, "쇼핑몰 판매물량")
                stock = safe_int(row, "기말 재고")

                # ✅ channels
                channels = ["offline"]
                if online_name:
                    channels = ["online", "offline"]

                # ✅ Product
                product, _ = InventoryItem.objects.get_or_create(
                    product_id=product_id,
                    defaults={
                        "name": offline_name,
                        "online_name": online_name,
                        "category": safe_str(row, "카테고리"),
                        "big_category": safe_str(row, "대분류"),
                        "middle_category": safe_str(row, "중분류"),
                        "description": safe_str(row, "설명"),
                    },
                )

                # ✅ Variant (없으면 생성)
                variant, created = ProductVariant.objects.get_or_create(
                    variant_code=variant_code,
                    defaults={
                        "product": product,
                        "option": option,
                        "detail_option": detail_option,
                        "stock": stock,
                        "price": 0,
                        "min_stock": 0,
                        "channels": channels,
                        "is_active": True,
                    },
                )

                if created:
                    created_variants += 1
                else:
                    skipped_variants += 1

                # ✅ 기말 재고는 항상 동기화
                variant.stock = stock
                variant.save(update_fields=["stock"])

                # ✅ 월별 재고 스냅샷 생성 / 업데이트
                _, status_created = ProductVariantStatus.objects.update_or_create(
                    year=year,
                    month=month,
                    variant=variant,
                    defaults={
                        "product": product,
                        "warehouse_stock_start": warehouse_start,
                        "store_stock_start": store_start,
                        "inbound_quantity": inbound,
                        "store_sales": store_sales,
                        "online_sales": online_sales,
                    },
                )

                if status_created:
                    created_status += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        return Response(
            {
                "summary": {
                    "year": year,
                    "month": month,
                    "total_rows": len(df),
                    "created_variants": created_variants,
                    "skipped_variants": skipped_variants,
                    "created_status": created_status,
                    "errors": len(errors),
                },
                "errors": errors[:100],
            },
            status=status.HTTP_201_CREATED,
        )

class ProductVariantStatusListView(generics.ListAPIView):
    """
    GET: 월별 재고 현황 조회 (year, month 필수)
    """
    permission_classes = [AllowAny]
    serializer_class = ProductVariantStatusSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
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
    - stock_adjustment
    - stock_adjustment_reason
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
    filter_backends = [DjangoFilterBackend, OrderingFilter]
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
                ),
                "created_by": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="김정현",
                    description="조정 작업자",
                ),
            },
        ),
        responses={201: InventoryAdjustmentSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
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
