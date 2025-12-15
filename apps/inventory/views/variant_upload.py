
# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Serializer, Model

from ..models import (
    InventoryItem,
    ProductVariant,
    ProductVariantStatus
)

from django.utils import timezone
import pandas as pd


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
