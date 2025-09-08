import io
from datetime import timedelta

import pandas as pd
import openpyxl, xlrd
import os, uuid, json
from django.conf import settings
from django.forms.models import model_to_dict


from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import F, Sum, ExpressionWrapper, IntegerField

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser

from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import InventoryItem, ProductVariant, InventoryAdjustment
from .serializers import (
    ProductOptionSerializer,
    ProductVariantSerializer,
    ProductVariantFullUpdateSerializer,
    InventoryItemWithVariantsSerializer,
    ProductVariantCreateSerializer,
    InventoryAdjustmentSerializer,
)
from apps.orders.models import OrderItem
from apps.supplier.models import SupplierVariant
from .filters import ProductVariantFilter, InventoryAdjustmentFilter


# 빠른 값 조회용 엔드포인트
class ProductOptionListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 옵션 리스트 조회",
        operation_description="상품 드롭다운용으로 product_id와 name만 간단히 반환합니다.",
        responses={200: ProductOptionSerializer(many=True)},
    )
    def get(self, request):
        products = InventoryItem.objects.all().only("product_id", "name")
        serializer = ProductOptionSerializer(products, many=True)
        return Response(serializer.data)


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


# 상품 CSV 업로드
class ProductVariantCSVUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]

    def generate_variant_code(self, base_code):
        existing = ProductVariant.objects.filter(
            variant_code__startswith=base_code
        ).values_list("variant_code", flat=True)
        suffix = ord("A")
        while True:
            candidate = f"{base_code}000{chr(suffix)}"
            if candidate not in existing:
                return candidate
            suffix += 1

    def infer_sheet_type(self, df: pd.DataFrame) -> str:
        if "상품 품목코드" in df.columns and "옵션" in df.columns:
            return "variant_detail"
        elif "바코드" in df.columns and "매출건수" in df.columns:
            return "sales_summary"
        else:
            return "unknown"

    @swagger_auto_schema(
        operation_summary="상품 XLSX 일괄 업로드",
        operation_description="엑셀 파일을 업로드하여 상품 및 상세 품목 정보를 일괄 생성 또는 업데이트합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 XLSX 파일",
            )
        ],
        responses={200: "성공", 400: "파일 에러 또는 유효성 오류"},
    )
    def post(self, request):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response(
                {"error": "파일이 첨부되지 않았습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            filename = excel_file.name
            batch_id = self._batch_start(filename)

            if filename.endswith(".xls"):
                df = pd.read_excel(excel_file, engine="xlrd")
            else:  # 기본은 .xlsx
                df = pd.read_excel(excel_file, engine="openpyxl")
        except Exception as e:
            return Response(
                {"error": f"엑셀 파일을 읽을 수 없습니다: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sheet_type = self.infer_sheet_type(df)

        if sheet_type == "variant_detail":
            return self.process_variant_detail(df)
        elif sheet_type == "sales_summary":
            return self.process_sales_summary(df)
        else:
            return Response(
                {"error": "파일 형식을 인식할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if resp.status_code == 200:
            self._batch_commit()
            data = resp.data if isinstance(resp.data, dict) else {}
            data["batch_id"] = self._batch["batch_id"]
            return Response(data, status=200)
        return resp

    def process_variant_detail(self, df):
        required_cols = [
            "상품코드",
            "상품명",
            "상품 품목코드",
            "옵션",
            "판매가",
            "재고",
            "판매수량",
            "환불수량",
        ]
        for col in required_cols:
            if col not in df.columns:
                return Response(
                    {"error": f"필수 컬럼이 누락되었습니다: {col}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        created, updated, errors = [], [], []

        with transaction.atomic():
            for i, row in df.iterrows():
                try:
                    product_id = str(row["상품코드"]).strip()
                    product_name = str(row["상품명"]).strip()
                    option = (
                        str(row["옵션"]).strip() if pd.notnull(row["옵션"]) else "기본"
                    )
                    if not option:
                        option = "기본"

                    raw_code = row["상품 품목코드"]
                    variant_code = (
                        str(raw_code).strip()
                        if pd.notna(raw_code) and str(raw_code).strip() not in ["", "-"]
                        else self.generate_variant_code(product_id)
                    )

                    price = int(row["판매가"]) if pd.notnull(row["판매가"]) else 0
                    delta_stock = int(row["재고"]) if pd.notnull(row["재고"]) else 0
                    delta_order = (
                        int(row["판매수량"]) if pd.notnull(row["판매수량"]) else 0
                    )
                    delta_return = (
                        int(row["환불수량"]) if pd.notnull(row["환불수량"]) else 0
                    )

                    product, _ = InventoryItem.objects.get_or_create(
                        product_id=product_id, defaults={"name": product_name}
                    )

                    if option == "기본":
                        variant = ProductVariant.objects.filter(
                            product=product, option="기본"
                        ).first()
                    else:
                        variant = ProductVariant.objects.filter(
                            variant_code=variant_code
                        ).first()

                    # ... 생략 ...

                    if variant:
                        self._snapshot_before("update", variant=variant)
                        variant.option = option
                        variant.price = price
                        # 핵심 수정: 판매/환불을 반영해서 재고 보정
                        variant.stock += delta_stock - delta_order + delta_return
                        variant.order_count += delta_order
                        variant.return_count += delta_return
                        variant.save()
                        updated.append(ProductVariantSerializer(variant).data)
                    else:
                        self._snapshot_before("create", variant_code=variant_code)
                        # 핵심 수정: 신규 생성도 판매/환불 반영된 초기 재고로 저장
                        variant = ProductVariant.objects.create(
                            product=product,
                            variant_code=variant_code,
                            option=option,
                            price=price,
                            stock=(delta_stock - delta_order + delta_return),  # << 여기
                            order_count=delta_order,
                            return_count=delta_return,
                        )
                        created.append(ProductVariantSerializer(variant).data)
                except Exception as e:
                    errors.append(f"{i+2}행: {str(e)}")

        return Response(
            {
                "type": "variant_detail",
                "created_count": len(created),
                "updated_count": len(updated),
                "created": created,
                "updated": updated,
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )

    # 배치로 업데이트 전 히스토리 저장
    def _new_batch_id(self):
        return timezone.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]

    def _batch_path(self, batch_id: str):
        base = getattr(settings, "MEDIA_ROOT", os.path.join(os.getcwd(), "media"))
        folder = os.path.join(base, "import_backups")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{batch_id}.json")

    def _batch_start(self, filename: str):
        self._batch = {
            "batch_id": self._new_batch_id(),
            "filename": filename,
            "snapshots": [],  # [{action, variant_code, before}]
        }
        self._batch_file = self._batch_path(self._batch["batch_id"])
        return self._batch["batch_id"]

    def _snapshot_before(
        self, action: str, variant=None, variant_code: str | None = None
    ):
        """
        action: 'create' | 'update'
        - update: 현재 DB값을 before로 저장
        - create: 생성될 코드만 기록 (before=None)
        """
        before = model_to_dict(variant) if variant is not None else None
        code = variant.variant_code if variant is not None else variant_code
        self._batch["snapshots"].append(
            {
                "action": action,
                "variant_code": code,
                "before": before,
            }
        )

    def _batch_commit(self):
        # 업로드 전체가 성공한 경우에만 파일 저장
        with open(self._batch_file, "w", encoding="utf-8") as f:
            json.dump(self._batch, f, ensure_ascii=False, indent=2)

    def process_sales_summary(self, df):

        required_cols = [
            "바코드",
            "분류명",
            "상품명",
            "판매가",
            "매출건수",
        ]  # 변경: 오프라인 업로드에 매출 반영이 필수이므로 '매출건수'를 추가
        for col in required_cols:
            if col not in df.columns:
                return Response(
                    {"error": f"필수 컬럼이 누락되었습니다: {col}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        created = []
        updated = []
        errors = []

        with transaction.atomic():
            for i, row in df.iterrows():
                try:
                    barcode = str(row["바코드"]).strip()
                    if not barcode or barcode.lower() == "nan" or barcode == "-":
                        continue

                    category = (
                        str(row["분류명"]).strip()
                        if pd.notnull(row["분류명"])
                        else "일반"
                    )
                    name = str(row["상품명"]).strip()
                    price = int(row["판매가"]) if pd.notnull(row["판매가"]) else 0
                    sales_count = (
                        int(row["매출건수"]) if pd.notnull(row["매출건수"]) else 0
                    )

                    product, created_flag = InventoryItem.objects.get_or_create(
                        product_id=barcode,
                        defaults={"name": name, "category": category},
                    )
                    if not created_flag:
                        product.name = name
                        product.category = category
                        product.save()

                    variant, variant_created = ProductVariant.objects.get_or_create(
                        product=product,
                        option="기본",
                        defaults={
                            "variant_code": self.generate_variant_code(barcode),
                            "price": price,
                            "stock": 0,
                            "order_count": 0,
                            "return_count": 0,
                        },
                    )

                    if variant_created:
                        self._snapshot_before(
                            "create", variant_code=variant.variant_code
                        )
                        # 변경: 오프라인 '매출건수'를 결제수량(order_count)에 누적하고, 재고(stock)에서 차감
                        ProductVariant.objects.filter(pk=variant.pk).update(  #
                            price=price,
                            order_count=F("order_count") + sales_count,
                            stock=F("stock") - sales_count,
                        )
                        variant.refresh_from_db()  #
                        created.append(ProductVariantSerializer(variant).data)
                    else:
                        self._snapshot_before("update", variant=variant)
                        # 변경: 기존 variant에도 동일하게 결제수량 누적 + 재고 차감
                        ProductVariant.objects.filter(pk=variant.pk).update(
                            price=price,
                            order_count=F("order_count") + sales_count,
                            stock=F("stock") - sales_count,
                        )
                        variant.refresh_from_db()
                        updated.append(ProductVariantSerializer(variant).data)

                except Exception as e:
                    errors.append(f"{i+2}행: {str(e)}")

        return Response(
            {
                "type": "sales_summary",
                "created_count": len(created),
                "updated_count": len(updated),
                "errors": errors,
                "created": created,
                "updated": updated,
            },
            status=status.HTTP_200_OK,
        )


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
                "suppliers": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="공급자 매핑 목록",
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        required=["name", "cost_price", "is_primary"],
                        properties={
                            "name": openapi.Schema(
                                type=openapi.TYPE_STRING, example="넥스트물류"
                            ),
                            "cost_price": openapi.Schema(
                                type=openapi.TYPE_INTEGER, example=3016
                            ),
                            "is_primary": openapi.Schema(
                                type=openapi.TYPE_BOOLEAN, example=True
                            ),
                        },
                    ),
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
                "suppliers": [
                    {"name": "넥스트물류", "cost_price": 3016, "is_primary": True}
                ],
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

        if not created and not product.is_active:
            product.is_active = True
            product.name = product_name
            product.save()

        variant_code = self.generate_variant_code(product.product_id)

        serializer = ProductVariantFullUpdateSerializer(
            data=request.data, context={"product": product, "request": request}
        )
        if serializer.is_valid():
            serializer.save(variant_code=variant_code)
            return Response(
                ProductVariantSerializer(serializer.instance).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="상품 상세 목록 조회",
        tags=["inventory - Variant CRUD"],
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
        tags=["inventory - Variant CRUD"],
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
                "suppliers": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "name": openapi.Schema(
                                type=openapi.TYPE_STRING, example="넥스트물류"
                            ),
                            "cost_price": openapi.Schema(
                                type=openapi.TYPE_INTEGER, example=3016
                            ),
                            "is_primary": openapi.Schema(
                                type=openapi.TYPE_BOOLEAN, example=True
                            ),
                        },
                    ),
                ),
            },
        ),
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"},
    )
    def patch(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantFullUpdateSerializer(
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
        tags=["inventory - Variant CRUD"],
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


# 동일 상품 다른 id 하나로 병합하기
class InventoryItemMergeView(APIView):
    """
    POST: 동일 상품이지만 id가 다른 상품을 하나로 병합용
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 코드 병합",
        operation_description="여러 variant(source_variant_codes)를 target_variant_code로 병합합니다. 병합된 variant들은 삭제되고, 연관된 product도 통합됩니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["target_variant_code", "source_variant_codes"],
            properties={
                "target_variant_code": openapi.Schema(
                    type=openapi.TYPE_STRING, description="최종 남길 variant_code"
                ),
                "source_variant_codes": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="합칠(삭제할) variant_code 리스트",
                ),
            },
        ),
        responses={204: "Merge completed.", 400: "Bad Request", 404: "Not Found"},
    )
    def post(self, request):
        target_variant_code = request.data.get(
            "target_variant_code"
        )  # 병합 대상 variant_code (최종적으로 남는 코드)
        # 병합 필요 variant_code (fade out되는 코드들)
        source_variant_codes = request.data.get("source_variant_codes")

        if not isinstance(source_variant_codes, list) or not target_variant_code:
            return Response(
                {
                    "error": "target_variant_code와 source_variant_codes(리스트)를 모두 제공해야 합니다."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_variant_code in source_variant_codes:
            return Response(
                {
                    "error": "target_variant_code는 source_variant_codes에 포함될 수 없습니다."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure target variant exists
        try:
            target_variant = ProductVariant.objects.get(
                variant_code=target_variant_code
            )
        except ProductVariant.DoesNotExist:
            return Response(
                {
                    "error": "target_variant_code에 해당하는 variant가 존재하지 않습니다."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        source_variant_codes = [
            code for code in source_variant_codes if code != target_variant_code
        ]
        source_variants = ProductVariant.objects.filter(
            variant_code__in=source_variant_codes
        )

        if not source_variants.exists():
            return Response(
                {"error": "합칠 source_variant_codes에 유효한 variant가 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute merge within transaction
        with transaction.atomic():
            # 1) 모든 source variant들의 데이터를 target variant로 병합
            self._merge_variant_data(target_variant, source_variants)

            # 2) Source variant들과 연관된 product 정리
            self._cleanup_orphaned_products(source_variants, target_variant.product)

            # 3) Source variant들 삭제
            source_variants.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _merge_variant_data(self, target_variant, source_variants):
        # 재고 합산
        total_stock = target_variant.stock
        total_adjustment = target_variant.adjustment

        for source_variant in source_variants:
            total_stock += source_variant.stock
            total_adjustment += source_variant.adjustment

        target_variant.stock = total_stock
        target_variant.adjustment = total_adjustment
        target_variant.save()

        # 관련 객체 업데이트 (ORM 방식)
        InventoryAdjustment.objects.filter(variant__in=source_variants).update(
            variant=target_variant
        )
        OrderItem.objects.filter(variant__in=source_variants).update(
            variant=target_variant
        )
        SupplierVariant.objects.filter(variant__in=source_variants).update(
            variant=target_variant
        )

    def _cleanup_orphaned_products(self, source_variants, target_product):
        """
        Source variant들이 삭제된 후 고아가 되는 product들을 정리
        """
        # Source variant들의 product들을 찾음
        source_products = set()
        for variant in source_variants:
            if variant.product.id != target_product.id:
                source_products.add(variant.product)

        # 각 source product가 다른 variant를 가지고 있는지 확인
        for product in source_products:
            # 현재 삭제될 variant들을 제외한 다른 variant가 있는지 확인
            remaining_variants = ProductVariant.objects.filter(product=product).exclude(
                id__in=[v.id for v in source_variants]
            )

            # 다른 variant가 없으면 product 비활성화
            if not remaining_variants.exists():
                product.is_active = False
                product.save()


################ 재고 조정
# 재고 업데이트
class StockUpdateView(APIView):
    """
    PUT: 재고량 수동 업데이트
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="재고량 수동 업데이트",
        tags=["inventory - Stock"],
        operation_description="실사 재고량을 입력하여 재고를 업데이트하고 조정 이력을 자동 생성합니다.",
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
            required=["actual_stock"],
            properties={
                "actual_stock": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="실사한 실제 재고량",
                    example=125,
                ),
                "reason": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="조정 사유",
                    example="2025년 2분기 실사",
                ),
                "updated_by": openapi.Schema(
                    type=openapi.TYPE_STRING, description="작업자", example="유시진"
                ),
            },
        ),
        responses={200: "Stock updated successfully", 404: "Not Found"},
    )
    def put(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=404)

        actual_stock = request.data.get("actual_stock")
        if actual_stock is None:
            return Response({"error": "actual_stock is required"}, status=400)

        if actual_stock < 0:
            return Response({"error": "actual_stock cannot be negative"}, status=400)

        # 현재 총 재고량 (stock + adjustment)
        current_total_stock = variant.stock + variant.adjustment
        delta = actual_stock - current_total_stock

        # 조정이 필요한 경우에만 처리
        if delta != 0:
            # 조정 이력 생성 (감사 추적용)
            InventoryAdjustment.objects.create(
                variant=variant,
                delta=delta,
                reason=request.data.get("reason", "재고 실사"),
                created_by=request.data.get("updated_by", "unknown"),
            )

            # stock을 실제 재고로 업데이트, adjustment는 0으로 리셋
            variant.stock = actual_stock
            variant.adjustment = 0
            variant.save()

            return Response(
                {
                    "message": "재고 업데이트 완료",
                    "previous_total_stock": current_total_stock,
                    "new_stock": actual_stock,
                    "adjustment_delta": delta,
                    "updated_at": variant.updated_at,
                },
                status=200,
            )
        else:
            return Response(
                {
                    "message": "조정 불필요 - 재고가 일치합니다",
                    "current_stock": current_total_stock,
                },
                status=200,
            )


############ 재고 조정
class InventoryAdjustmentListView(generics.ListAPIView):
    """
    GET: 재고 조정 이력 전체 조회 또는 품목별 조회
    - variant_code로 필터 가능
    - 최신순 정렬 (기본 10건 페이지네이션)
    """

    permission_classes = [AllowAny]
    queryset = InventoryAdjustment.objects.select_related("variant__product").all()
    serializer_class = InventoryAdjustmentSerializer
    filterset_class = InventoryAdjustmentFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["variant__variant_code"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]  # 최신순 기본 정렬

    @swagger_auto_schema(
        operation_summary="재고 조정 이력 조회",
        tags=["inventory - Stock"],
        operation_description="variant_code 기준 필터링 및 페이지네이션 지원",
        manual_parameters=[
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="조회할 variant_code (예: P00000YC000A)",
            ),
            openapi.Parameter(
                name="page",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="페이지 번호 (기본=1)",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


###########CSV 업로드 후 롤백할 수 있는 엔드포인트 추가
class ProductVariantUploadRollbackView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="업로드 롤백",
        operation_description="CSV 업로드 배치(batch_id) 단위로 변경을 되돌립니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["batch_id"],
            properties={
                "batch_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="업로드 응답으로 받은 배치 ID"
                ),
            },
        ),
        responses={200: "Rollback completed", 404: "Batch not found"},
    )
    def post(self, request):
        batch_id = request.data.get("batch_id")
        if not batch_id:
            return Response({"error": "batch_id가 필요합니다."}, status=400)

        path = os.path.join(
            getattr(settings, "MEDIA_ROOT", os.path.join(os.getcwd(), "media")),
            "import_backups",
            f"{batch_id}.json",
        )
        if not os.path.exists(path):
            return Response(
                {"error": "해당 batch_id의 스냅샷 파일이 없습니다."}, status=404
            )

        with open(path, encoding="utf-8") as f:
            batch = json.load(f)

        snaps = batch.get("snapshots", [])

        # 역순 적용: 마지막 변경부터 되돌리기
        with transaction.atomic():
            for s in reversed(snaps):
                action = s.get("action")
                code = s.get("variant_code")
                before = s.get("before")

                if action == "create":
                    # 업로드에서 '생성된' 레코드는 삭제
                    ProductVariant.objects.filter(variant_code=code).delete()
                elif action == "update":
                    try:
                        v = ProductVariant.objects.get(variant_code=code)
                    except ProductVariant.DoesNotExist:
                        # 없으면 패스 (이미 수동삭제되었을 수도)
                        continue

                    # before 값으로 복구 (ID/타임스탬프는 제외)
                    for field, value in before.items():
                        if field in ("id", "created_at", "updated_at"):
                            continue
                        if field == "product":
                            # product는 FK id로 저장되어 있음
                            setattr(v, "product_id", value)
                        else:
                            setattr(v, field, value)
                    v.save()

        return Response(
            {"message": "Rollback completed", "batch_id": batch_id}, status=200
        )
