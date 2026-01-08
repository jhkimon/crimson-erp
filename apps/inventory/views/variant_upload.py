from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django.utils import timezone
from django.db import transaction

from apps.inventory.models import (
    InventoryItem,
    ProductVariant,
    ProductVariantStatus,
)

from apps.inventory.utils.excel import load_excel, safe_str, safe_int
from apps.inventory.utils.variant_code import build_variant_code
from apps.inventory.services.variant_resolver import resolve_variant


class ProductVariantExcelUploadView(APIView):
    """
    POST: 재고 관리 엑셀 업로드
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
            ),
            openapi.Parameter(
                name="year",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                name="month",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
            ),
        ],
    )
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "file is required"}, status=400)

        year = int(request.query_params.get("year", timezone.now().year))
        month = int(request.query_params.get("month", timezone.now().month))

        try:
            df = load_excel(file)
        except Exception as e:
            return Response({"error": f"엑셀 로드 실패: {str(e)}"}, status=400)

        REQUIRED_COLUMNS = [
            "상품코드",
            "오프라인 품목명",
            "온라인 품목명",
            "옵션",
            "상세옵션",
            "월초창고 재고",
            "월초매장 재고",
            "당월입고물량",
            "매장 판매물량",
            "쇼핑몰 판매물량",
        ]

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            return Response({"error": f"필수 컬럼 누락: {missing_cols}"}, status=400)

        created_variants = 0
        skipped_variants = 0
        created_status = 0

        try:
            with transaction.atomic():
                for _, row in df.iterrows():
                    raw_variant_code = safe_str(row, "상품코드")
                    product_name = safe_str(row, "오프라인 품목명") or "상품명 없음"
                    option = safe_str(row, "옵션")
                    detail_option = safe_str(row, "상세옵션")

                    # product_id 결정
                    if raw_variant_code and "-" in raw_variant_code:
                        product_id, parsed_detail = raw_variant_code.rsplit("-", 1)
                    else:
                        product_id = raw_variant_code

                    # variant_code 결정
                    if raw_variant_code:
                        variant_code = raw_variant_code

                    else:
                        variant_code = build_variant_code(
                            product_id=product_id or None,
                            product_name=product_name,
                            option=option,
                            detail_option=detail_option,
                            allow_auto=True,
                        )

                    option = option or ""

                    online_name = safe_str(row, "온라인 품목명")

                    warehouse_start = safe_int(row, "월초창고 재고")
                    store_start = safe_int(row, "월초매장 재고")
                    inbound = safe_int(row, "당월입고물량")
                    store_sales = safe_int(row, "매장 판매물량")
                    online_sales = safe_int(row, "쇼핑몰 판매물량")

                    channels = ["offline"]
                    if online_name:
                        channels = ["online", "offline"]

                    product, _ = InventoryItem.objects.get_or_create(
                        product_id=product_id,
                        defaults={
                            "name": product_name,
                            "online_name": online_name,
                            "category": safe_str(row, "카테고리"),
                            "big_category": safe_str(row, "대분류"),
                            "middle_category": safe_str(row, "중분류"),
                            "description": safe_str(row, "설명"),
                        },
                    )

                    variant = resolve_variant(
                        product=product,
                        option=option,
                        detail_option=detail_option,
                        variant_code=variant_code,
                    )

                    if variant:
                        skipped_variants += 1
                    else:
                        variant = ProductVariant.objects.create(
                            product=product,
                            option=option,
                            detail_option=detail_option,
                            variant_code=variant_code,
                            price=0,
                            min_stock=0,
                            channels=channels,
                            is_active=True,
                        )
                        created_variants += 1

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
            return Response(
                {
                    "error": "엑셀 업로드 중 오류 발생",
                    "detail": f"[{product_name}] {str(e)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "summary": {
                    "year": year,
                    "month": month,
                    "total_rows": len(df),
                    "created_variants": created_variants,
                    "skipped_variants": skipped_variants,
                    "created_status": created_status,
                }
            },
            status=status.HTTP_201_CREATED,
        )