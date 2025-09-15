import io
from datetime import timedelta

import pandas as pd
import openpyxl, xlrd
import os, uuid, json
from django.conf import settings
from django.forms.models import model_to_dict


from django.db import transaction, models
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

from .models import (
    InventoryItem,
    ProductVariant,
    InventoryAdjustment,
    InventorySnapshot,
    InventorySnapshotItem,
)
from .serializers import (
    ProductOptionSerializer,
    ProductVariantSerializer,
    ProductVariantFullUpdateSerializer,
    InventoryItemWithVariantsSerializer,
    ProductVariantCreateSerializer,
    InventoryAdjustmentSerializer,
    InventorySnapshotSerializer,
    InventorySnapshotItemSerializer,
    ProductMatchingRequestSerializer,
    ProductMatchingResponseSerializer,
    ProductPhysicalMergeRequestSerializer,
    ProductPhysicalMergePreviewSerializer,
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


class InventoryAdjustmentListView(generics.ListAPIView):
    """
    GET: 재고 조정 이력 전체 조회 또는 품목별 조회
    - variant_code로 필터 가능
    - 최신순 정렬 (기본 10건 페이지네이션)
    """

    permission_classes = [AllowAny]
    queryset = InventoryAdjustment.objects.select_related("variant").all()
    serializer_class = InventoryAdjustmentSerializer
    filterset_class = InventoryAdjustmentFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["variant__variant_code"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]  # 최신순 기본 정렬

    @swagger_auto_schema(
        operation_summary="재고 조정 이력 조회",
        tags=["inventory - Stock Adjust"],
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
        return super().get(request, *args, kwargs)


# --- Utils: 현재 재고 상태를 스냅샷으로 저장 ---
@transaction.atomic
def create_inventory_snapshot(
    reason: str = "", actor=None, meta: dict | None = None
) -> InventorySnapshot:
    snap = InventorySnapshot.objects.create(
        reason=reason or "",
        actor=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
        meta=meta or {},
    )

    # 현재 ProductVariant 전체를 조인해서 스냅샷 아이템으로 생성
    qs = (
        ProductVariant.objects.select_related("product")  # InventoryItem
        # .prefetch_related(...)    # 필요 시 공급처 등 프리패치
    )

    items = []
    for v in qs:
        p = v.product
        items.append(
            InventorySnapshotItem(
                snapshot=snap,
                variant=v,
                product_id=p.product_id,
                name=p.name,
                category=p.category,
                variant_code=v.variant_code,
                option=v.option,
                stock=v.stock,
                price=v.price,
                cost_price=v.cost_price,
                order_count=v.order_count,
                return_count=v.return_count,
                sales=getattr(v, "sales", 0),
            )
        )
    InventorySnapshotItem.objects.bulk_create(items, batch_size=1000)
    return snap


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
        operation_summary="POS 데이터 업로드 (스냅샷 자동 생성)",
        tags=["inventory - Upload"],
        operation_description="""
        **POS 데이터(xlsx/xls)를 업로드하여 재고를 업데이트합니다.**
        
        **자동 처리 프로세스:**
        1. 업로드 전 현재 재고 상태를 스냅샷으로 자동 저장
        2. 업로드된 데이터로 상품/재고 정보 덮어쓰기
        3. 처리 결과 및 생성된 스냅샷 ID 반환
        
        **지원 파일 형식:**
        - **상품 상세 시트**: 상품 품목코드, 옵션 컬럼 포함
        - **매출 요약 시트**: 바코드, 매출건수 컬럼 포함
        
        **롤백 방법:**
        - 문제가 생긴 경우 `POST /inventory/rollback/{snapshot_id}` 사용
        - 업로드 전 상태로 완전 복원 가능
        
        **주의사항:**
        - 이 작업은 기존 데이터를 덮어씁니다
        - 반드시 백업된 스냅샷 ID를 기록해두세요
        """,
        manual_parameters=[
            openapi.Parameter(
                name="file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 XLSX/XLS 파일",
            ),
            openapi.Parameter(
                name="reason",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=False,
                description="업로드 사유 (선택사항)",
            ),
        ],
        responses={
            200: openapi.Response(
                description="업로드 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, example="POS 데이터 업로드 완료"
                        ),
                        "snapshot_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=123,
                            description="업로드 전 생성된 스냅샷 ID",
                        ),
                        "batch_id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="20250911-abc123",
                            description="업로드 배치 ID",
                        ),
                        "type": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="variant_detail",
                            description="처리된 시트 타입",
                        ),
                        "created_count": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=50,
                            description="신규 생성된 상품 수",
                        ),
                        "updated_count": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=100,
                            description="업데이트된 상품 수",
                        ),
                        "errors": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING),
                            description="처리 오류 목록",
                        ),
                    },
                ),
            ),
            400: openapi.Response(
                description="파일 오류 또는 유효성 검증 실패",
                examples={
                    "application/json": {
                        "error": "엑셀 파일을 읽을 수 없습니다: Invalid file format"
                    }
                },
            ),
        },
    )
    def post(self, request):
        excel_file = request.FILES.get("file")
        reason = request.data.get("reason", "POS 데이터 업로드")

        if not excel_file:
            return Response(
                {"error": "파일이 첨부되지 않았습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. 업로드 전 현재 재고 상태 스냅샷 생성
        snapshot = create_inventory_snapshot(
            reason=f"업로드 전 백업 - {reason}",
            actor=request.user if request.user.is_authenticated else None,
            meta={
                "filename": excel_file.name,
                "filesize": excel_file.size,
                "upload_reason": reason,
                "upload_type": "pos_data",
            },
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

        try:
            if sheet_type == "variant_detail":
                resp = self.process_variant_detail(df)
            elif sheet_type == "sales_summary":
                resp = self.process_sales_summary(df)
            else:
                return Response(
                    {
                        "error": "파일 형식을 인식할 수 없습니다. '상품 품목코드' 또는 '바코드' 컬럼이 필요합니다."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if resp.status_code == 200:
                self._batch_commit()
                data = resp.data if isinstance(resp.data, dict) else {}
                data["batch_id"] = self._batch["batch_id"]
                data["snapshot_id"] = snapshot.id  # 스냅샷 ID 추가
                data["message"] = "POS 데이터 업로드 완료"
                return Response(data, status=200)
            else:
                return resp

        except Exception as e:
            return Response(
                {"error": f"데이터 처리 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        tags=["inventory - Stock Adjust"],
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


############ POS 데이터 업로드 후 롤백
class InventoryRollbackView(APIView):
    """
    POST /inventory/rollback/{id} : 특정 스냅샷으로 재고 롤백
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="재고 롤백 (스냅샷 복원)",
        tags=["inventory"],
        operation_description="""
        **지정된 스냅샷 시점으로 재고를 되돌립니다.**
        
        **자동 처리 프로세스:**
        1. 롤백 전 현재 재고 상태를 백업 스냅샷으로 자동 저장
        2. 지정된 스냅샷의 재고 데이터로 ProductVariant 테이블 덮어쓰기
        3. 처리 결과 및 백업 스냅샷 ID 반환
        
        **복원되는 데이터:**
        - stock (재고)
        - price (판매가)
        - cost_price (원가)
        - order_count (주문수량)
        - return_count (반품수량)
        
        **사용 예시:**
        - 잘못된 POS 업로드 후 이전 상태로 복원
        - 실수로 변경된 재고 데이터 되돌리기
        - 특정 시점의 재고 상태로 복구
        
        **주의사항:**
        - 롤백 후에는 다시 되돌릴 수 없습니다 (새 백업 스냅샷 사용)
        - variant_code가 존재하지 않는 항목은 건너뜁니다
        """,
        manual_parameters=[
            openapi.Parameter(
                name="id",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="롤백할 스냅샷 ID",
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "reason": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="롤백 사유",
                    example="잘못된 POS 업로드 되돌리기",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="롤백 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, example="롤백 완료"
                        ),
                        "rollback_snapshot_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=123,
                            description="롤백한 스냅샷 ID",
                        ),
                        "backup_snapshot_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=124,
                            description="롤백 전 생성된 백업 스냅샷 ID",
                        ),
                        "updated_count": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=450,
                            description="업데이트된 상품 수",
                        ),
                        "skipped_count": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            example=5,
                            description="존재하지 않아 건너뛴 상품 수",
                        ),
                        "rollback_date": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="2025-09-11T09:30:00+09:00",
                            description="롤백한 스냅샷 생성일시",
                        ),
                    },
                ),
            ),
            404: openapi.Response(
                description="스냅샷을 찾을 수 없음",
                examples={"application/json": {"error": "스냅샷을 찾을 수 없습니다."}},
            ),
            500: "롤백 처리 중 오류 발생",
        },
    )
    def post(self, request, id):
        try:
            target_snapshot = InventorySnapshot.objects.get(id=id)
        except InventorySnapshot.DoesNotExist:
            return Response(
                {"error": "스냅샷을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reason = request.data.get("reason", f"스냅샷 #{id}로 롤백")

        try:
            with transaction.atomic():
                # 1. 롤백 전 현재 상태 백업
                backup_snapshot = create_inventory_snapshot(
                    reason=f"롤백 전 백업 - {reason}",
                    actor=request.user if request.user.is_authenticated else None,
                    meta={
                        "rollback_target_snapshot_id": id,
                        "rollback_target_date": target_snapshot.created_at.isoformat(),
                        "rollback_reason": reason,
                        "operation_type": "rollback_backup",
                    },
                )

                # 2. 타겟 스냅샷 데이터로 ProductVariant 업데이트
                updated_count, skipped_count = self._rollback_to_snapshot(
                    target_snapshot
                )

                return Response(
                    {
                        "message": "롤백 완료",
                        "rollback_snapshot_id": id,
                        "backup_snapshot_id": backup_snapshot.id,
                        "updated_count": updated_count,
                        "skipped_count": skipped_count,
                        "rollback_date": target_snapshot.created_at.isoformat(),
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response(
                {"error": f"롤백 처리 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _rollback_to_snapshot(self, snapshot):
        """스냅샷 데이터로 ProductVariant 필드들을 업데이트"""
        snapshot_items = snapshot.items.all()
        updated_count = 0
        skipped_count = 0

        # 배치 업데이트를 위한 리스트
        variants_to_update = []

        for item in snapshot_items:
            try:
                # variant_code로 ProductVariant 찾기
                variant = ProductVariant.objects.select_for_update().get(
                    variant_code=item.variant_code
                )

                # 스냅샷 데이터로 필드 업데이트
                variant.stock = item.stock
                variant.price = item.price
                variant.cost_price = item.cost_price
                variant.order_count = item.order_count
                variant.return_count = item.return_count

                variants_to_update.append(variant)
                updated_count += 1

            except ProductVariant.DoesNotExist:
                # 해당 variant_code가 더 이상 존재하지 않는 경우 건너뛰기
                skipped_count += 1
                continue

        # 배치 업데이트 수행
        if variants_to_update:
            ProductVariant.objects.bulk_update(
                variants_to_update,
                ["stock", "price", "cost_price", "order_count", "return_count"],
                batch_size=1000,
            )

        return updated_count, skipped_count


class InventorySnapshotListCreateView(generics.ListCreateAPIView):
    """
    GET  /snapshot   : 스냅샷 목록(메타만; items 제외)
    POST /snapshot   : 현재 재고 상태 스냅샷 생성
    """

    queryset = InventorySnapshot.objects.order_by("-created_at")
    serializer_class = InventorySnapshotSerializer

    # 목록에선 items를 빼서 가볍게 반환
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # PageNumberPagination 사용 시 'results' 키, 아니면 전체 리스트
        if isinstance(response.data, dict) and "results" in response.data:
            for obj in response.data["results"]:
                obj.pop("items", None)
        else:
            # pagination 미사용 시
            for obj in response.data:
                obj.pop("items", None)
        return response

    # 생성은 커스텀 유틸 호출
    def create(self, request, *args, **kwargs):
        reason = request.data.get("reason", "")
        meta = request.data.get("meta", {}) or {}

        snap = create_inventory_snapshot(
            reason=reason,
            actor=request.user if request.user.is_authenticated else None,
            meta=meta,
        )
        data = self.get_serializer(snap).data
        return Response(data, status=status.HTTP_201_CREATED)


class InventorySnapshotRetrieveView(generics.RetrieveAPIView):
    """
    GET /snapshot/<id> : 스냅샷 단건(아이템 포함) 조회
    """

    serializer_class = InventorySnapshotSerializer
    lookup_field = "id"
    queryset = InventorySnapshot.objects.all()
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="재고 스냅샷 상세 조회",
        tags=["inventory"],
        operation_description="""
        **특정 스냅샷의 상세 정보를 조회합니다.**
        
        **포함되는 데이터:**
        - 스냅샷 메타정보 (생성일시, 사유, 수행자)
        - 당시 모든 상품의 재고 상태 (items 배열)
        - 각 상품별 재고, 가격, 주문/반품 수량 등
        
        **사용 예시:**
        - 롤백 전 특정 시점의 재고 상태 확인
        - 재고 변화 추적 및 분석
        - 문제 발생 시점 데이터 검증
        
        **주의사항:**
        - 큰 데이터가 포함되므로 필요할 때만 호출
        - 목록 조회는 `GET /inventory/snapshot` 사용
        """,
        manual_parameters=[
            openapi.Parameter(
                name="id",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="조회할 스냅샷 ID",
            )
        ],
        responses={
            200: openapi.Response(
                description="스냅샷 상세 조회 성공",
                examples={
                    "application/json": {
                        "id": 123,
                        "created_at": "2025-09-11T10:15:00+09:00",
                        "reason": "업로드 전 백업 - 9월 POS 데이터",
                        "actor_name": "배연준",
                        "meta": {"filename": "pos_0911.xlsx"},
                        "items": [
                            {
                                "id": 1001,
                                "variant_code": "P00000YC000A",
                                "product_id": "P00000YC",
                                "name": "방패 필통",
                                "category": "문구",
                                "option": "크림슨",
                                "stock": 50,
                                "price": 5900,
                                "cost_price": 3000,
                                "order_count": 10,
                                "return_count": 1,
                                "sales": 0,
                            }
                        ],
                    }
                },
            ),
            404: "스냅샷을 찾을 수 없음",
        },
    )
    def get(self, request, *args, **kwargs):
        """스냅샷 상세 조회"""
        return super().get(request, *args, **kwargs)


## 동일 상품 매칭
class ProductMatchingView(APIView):
    """
    상품명 기반 온라인-오프라인 상품 매칭 API

    GET  /products/match  : 매칭 가능한 상품 목록 미리보기
    POST /products/match  : 상품명 기반 매칭 및 관리코드 부여
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품명 기반 매칭 및 관리코드 부여",
        operation_description="""
        **온라인과 오프라인 상품을 상품명 기준으로 매칭합니다.**
        
        **처리 과정:**
        1. management_code가 비어있는 오프라인 상품들을 조회
        2. 온라인 상품들과 상품명으로 완전 일치 검색
        3. 매칭 결과를 반환 (auto_apply=true시 자동으로 관리코드 부여)
        
        **매칭 상태:**
        - **matched**: 새로 매칭된 상품
        - **already_matched**: 이미 관리코드가 부여된 상품
        - **no_match**: 매칭되는 온라인 상품이 없음
        """,
        tags=["inventory - Product Matching"],
        request_body=ProductMatchingRequestSerializer,
        responses={200: ProductMatchingResponseSerializer, 400: "Bad Request"},
    )
    def post(self, request):
        serializer = ProductMatchingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        auto_apply = serializer.validated_data.get("auto_apply", False)

        # 1. 오프라인 상품들 (management_code가 비어있는 것들)
        offline_products = InventoryItem.objects.filter(
            models.Q(management_code__isnull=True) | models.Q(management_code="")
        ).values("product_id", "name")

        # 2. 온라인 상품들 (ProductVariant를 통해 조회)
        online_products = ProductVariant.objects.select_related("product").values(
            "variant_code", "product__name"
        )

        # 3. 이미 매칭된 오프라인 상품들
        already_matched = InventoryItem.objects.exclude(
            models.Q(management_code__isnull=True) | models.Q(management_code="")
        ).values("product_id", "name", "management_code")

        # 4. 매칭 로직 수행
        matches = []
        matched_count = 0
        applied_matches = []

        # 온라인 상품명을 키로 하는 딕셔너리 생성
        online_dict = {
            product["product__name"]: product["variant_code"]
            for product in online_products
        }

        # 오프라인 상품들과 매칭 시도
        for offline_product in offline_products:
            offline_name = offline_product["name"]
            offline_id = offline_product["product_id"]

            if offline_name in online_dict:
                # 매칭 성공
                online_variant_code = online_dict[offline_name]
                matches.append(
                    {
                        "offline_product_id": offline_id,
                        "offline_product_name": offline_name,
                        "online_variant_code": online_variant_code,
                        "online_product_name": offline_name,  # 같은 이름이므로
                        "match_status": "matched",
                    }
                )
                matched_count += 1

                # auto_apply가 True면 실제로 관리코드 부여
                if auto_apply:
                    applied_matches.append(
                        {
                            "product_id": offline_id,
                            "management_code": online_variant_code,
                        }
                    )
            else:
                # 매칭 실패
                matches.append(
                    {
                        "offline_product_id": offline_id,
                        "offline_product_name": offline_name,
                        "online_variant_code": None,
                        "online_product_name": None,
                        "match_status": "no_match",
                    }
                )

        # 이미 매칭된 상품들도 결과에 포함
        for matched_product in already_matched:
            matches.append(
                {
                    "offline_product_id": matched_product["product_id"],
                    "offline_product_name": matched_product["name"],
                    "online_variant_code": matched_product["management_code"],
                    "online_product_name": matched_product["name"],
                    "match_status": "already_matched",
                }
            )

        # 5. auto_apply가 True인 경우 실제 DB 업데이트
        applied = False
        if auto_apply and applied_matches:
            with transaction.atomic():
                for match in applied_matches:
                    InventoryItem.objects.filter(product_id=match["product_id"]).update(
                        management_code=match["management_code"]
                    )
                applied = True

        # 6. 응답 데이터 구성
        response_data = {
            "total_offline_products": len(offline_products),
            "total_online_products": len(online_products),
            "matched_count": matched_count,
            "already_matched_count": len(already_matched),
            "no_match_count": len(offline_products) - matched_count,
            "matches": matches,
            "applied": applied,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="매칭 가능한 상품 목록 미리보기",
        operation_description="실제 매칭을 수행하지 않고 매칭 가능한 상품들을 미리 확인합니다.",
        tags=["inventory - Product Matching"],
        responses={200: ProductMatchingResponseSerializer},
    )
    def get(self, request):
        # POST와 동일한 로직이지만 auto_apply=False로 고정
        return self.post(request._clone_with_data({"auto_apply": False}))


class ProductMergeView(APIView):
    """
    같은 관리코드를 가진 온라인-오프라인 상품 통합 조회/관리

    GET /products/merge/{management_code}/  : 관리코드 기준 통합 상품 조회
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="관리코드 기준 통합 상품 조회",
        operation_description="""
        **같은 관리코드(품목코드)를 가진 온라인-오프라인 상품을 통합해서 조회합니다.**
        
        **통합 정보:**
        - 총 재고량 (온라인 + 오프라인)
        - 총 판매량 (온라인 + 오프라인)
        - 가격 정보
        - 상품 기본 정보
        """,
        tags=["inventory - Product Merge"],
        manual_parameters=[
            openapi.Parameter(
                "management_code",
                openapi.IN_PATH,
                description="통합 조회할 관리코드 (품목코드)",
                type=openapi.TYPE_STRING,
            )
        ],
        responses={200: "통합 상품 정보", 404: "Not Found"},
    )
    def get(self, request, management_code):
        # 1. 오프라인 상품 조회
        try:
            offline_product = InventoryItem.objects.get(management_code=management_code)
        except InventoryItem.DoesNotExist:
            offline_product = None

        # 2. 온라인 상품 조회
        try:
            online_variant = ProductVariant.objects.select_related("product").get(
                variant_code=management_code
            )
        except ProductVariant.DoesNotExist:
            online_variant = None

        if not offline_product and not online_variant:
            return Response(
                {"error": "해당 관리코드의 상품이 존재하지 않습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. 통합 정보 구성
        merged_data = {
            "management_code": management_code,
            "product_name": (
                offline_product.name if offline_product else online_variant.product.name
            ),
            "category": (
                offline_product.category
                if offline_product
                else online_variant.product.category
            ),
            "offline_data": None,
            "online_data": None,
            "merged_summary": {
                "total_stock": 0,
                "total_sales": 0,
                "total_order_count": 0,
                "total_return_count": 0,
            },
        }

        if offline_product:
            # 오프라인은 기본 variant 조회
            offline_variant = ProductVariant.objects.filter(
                product=offline_product, option="기본"
            ).first()

            merged_data["offline_data"] = {
                "product_id": offline_product.product_id,
                "stock": offline_variant.stock if offline_variant else 0,
                "price": offline_variant.price if offline_variant else 0,
                "order_count": offline_variant.order_count if offline_variant else 0,
                "return_count": offline_variant.return_count if offline_variant else 0,
            }

            if offline_variant:
                merged_data["merged_summary"]["total_stock"] += offline_variant.stock
                merged_data["merged_summary"][
                    "total_order_count"
                ] += offline_variant.order_count
                merged_data["merged_summary"][
                    "total_return_count"
                ] += offline_variant.return_count

        if online_variant:
            merged_data["online_data"] = {
                "variant_code": online_variant.variant_code,
                "option": online_variant.option,
                "stock": online_variant.stock,
                "price": online_variant.price,
                "order_count": online_variant.order_count,
                "return_count": online_variant.return_count,
            }

            merged_data["merged_summary"]["total_stock"] += online_variant.stock
            merged_data["merged_summary"][
                "total_order_count"
            ] += online_variant.order_count
            merged_data["merged_summary"][
                "total_return_count"
            ] += online_variant.return_count

        # 총 매출 계산
        net_sales = (
            merged_data["merged_summary"]["total_order_count"]
            - merged_data["merged_summary"]["total_return_count"]
        )
        if online_variant:
            merged_data["merged_summary"]["total_sales"] = (
                online_variant.price * net_sales
            )
        elif offline_product:
            offline_variant = ProductVariant.objects.filter(
                product=offline_product, option="기본"
            ).first()
            if offline_variant:
                merged_data["merged_summary"]["total_sales"] = (
                    offline_variant.price * net_sales
                )

        return Response(merged_data, status=status.HTTP_200_OK)


class MergeableProductsListView(generics.ListAPIView):
    """
    GET /mergeable-products : 병합 가능한 상품 목록 조회
    (management_code가 있고 variant_code와 매칭되는 상품들)
    """

    def get_queryset(self):
        # management_code가 있는 InventoryItem들
        return InventoryItem.objects.filter(management_code__isnull=False).exclude(
            management_code=""
        )

    def list(self, request, *args, **kwargs):
        try:
            offline_items = self.get_queryset()
            mergeable_products = []

            for item in offline_items:
                try:
                    # 해당 management_code와 같은 variant_code를 가진 온라인 상품이 있는지 확인
                    online_variant = ProductVariant.objects.get(
                        variant_code=item.management_code
                    )

                    # 오프라인 ProductVariant 확인
                    offline_variant = ProductVariant.objects.get(
                        product__inventoryitem=item, option="기본"
                    )

                    mergeable_products.append(
                        {
                            "management_code": item.management_code,
                            "offline_product_name": item.name,
                            "online_product_name": online_variant.product.name,
                            "offline_stock": offline_variant.stock_quantity or 0,
                            "online_stock": online_variant.stock_quantity or 0,
                            "total_stock_after_merge": (
                                offline_variant.stock_quantity or 0
                            )
                            + (online_variant.stock_quantity or 0),
                        }
                    )

                except ProductVariant.DoesNotExist:
                    # 매칭되는 온라인 상품이 없거나 오프라인 기본 옵션이 없는 경우 스킵
                    continue

            return Response(
                {
                    "success": True,
                    "mergeable_products": mergeable_products,
                    "total_count": len(mergeable_products),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"병합 가능한 상품 조회 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductMergeCreateView(generics.CreateAPIView):
    """
    POST /merge/product : 오프라인과 온라인 상품을 하나로 병합

    Request Body:
    {
        "management_code": "1234"  # 병합할 상품들의 공통 코드
    }
    """

    serializer_class = ProductPhysicalMergeRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        management_code = serializer.validated_data["management_code"]
        confirm = serializer.validated_data.get("confirm", False)

        # 확인하지 않은 경우 에러 반환
        if not confirm:
            return Response(
                {"error": "병합을 진행하려면 confirm을 true로 설정해주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # 1. management_code로 오프라인 InventoryItem 찾기
                offline_item = get_object_or_404(
                    InventoryItem, management_code=management_code
                )

                # 2. variant_code로 온라인 ProductVariant 찾기
                online_variant = get_object_or_404(
                    ProductVariant, variant_code=management_code
                )

                # 3. 오프라인 ProductVariant 찾기 (option="기본")
                offline_variant = get_object_or_404(
                    ProductVariant, product__inventoryitem=offline_item, option="기본"
                )

                # 4. 데이터 병합 (오프라인 → 온라인)
                # 재고 수량 합산
                online_variant.stock_quantity = (online_variant.stock_quantity or 0) + (
                    offline_variant.stock_quantity or 0
                )

                # 판매 수량 합산
                online_variant.sales_quantity = (online_variant.sales_quantity or 0) + (
                    offline_variant.sales_quantity or 0
                )

                # 가격 정보 (오프라인이 있으면 우선 적용, 없으면 온라인 유지)
                if offline_variant.price:
                    online_variant.price = offline_variant.price
                if offline_variant.cost_price:
                    online_variant.cost_price = offline_variant.cost_price
                if offline_variant.sale_price:
                    online_variant.sale_price = offline_variant.sale_price

                # 5. 온라인 Product명을 오프라인 InventoryItem명으로 변경
                online_product = online_variant.product
                original_online_name = online_product.name
                online_product.name = offline_item.name
                online_product.save()

                # 6. 온라인 ProductVariant 저장
                online_variant.save()

                # 7. 오프라인 데이터 삭제/비활성화
                offline_product = offline_variant.product
                offline_item_name = offline_item.name

                # ProductVariant 먼저 삭제
                offline_variant.delete()

                # InventoryItem 삭제
                offline_item.delete()

                # Product가 더 이상 연결된 variant가 없으면 삭제
                if not offline_product.variants.exists():
                    offline_product.delete()

                return Response(
                    {
                        "success": True,
                        "message": f'상품 "{offline_item_name}"이 성공적으로 병합되었습니다.',
                        "merged_product": {
                            "variant_code": online_variant.variant_code,
                            "product_name": online_product.name,
                            "stock_quantity": online_variant.stock_quantity,
                            "sales_quantity": online_variant.sales_quantity,
                            "price": (
                                str(online_variant.price)
                                if online_variant.price
                                else None
                            ),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )

        except InventoryItem.DoesNotExist:
            return Response(
                {
                    "error": f'관리코드 "{management_code}"에 해당하는 오프라인 상품을 찾을 수 없습니다.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except ProductVariant.DoesNotExist:
            return Response(
                {
                    "error": f'품목코드 "{management_code}"에 해당하는 온라인 상품을 찾을 수 없거나, 오프라인 상품의 기본 옵션을 찾을 수 없습니다.'
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {"error": f"병합 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BatchProductMergeView(APIView):
    """
    POST /batch/merge/products : 여러 상품을 한번에 병합

    Request Body:
    {
        "management_codes": ["1234", "5678", "9999"]
    }
    """

    def post(self, request, *args, **kwargs):
        management_codes = request.data.get("management_codes", [])

        if not management_codes:
            return Response(
                {"error": "병합할 관리코드 목록이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = {"success": [], "failed": []}

        for code in management_codes:
            try:
                with transaction.atomic():
                    # 단일 병합 로직과 동일
                    offline_item = InventoryItem.objects.get(management_code=code)
                    online_variant = ProductVariant.objects.get(variant_code=code)
                    offline_variant = ProductVariant.objects.get(
                        product__inventoryitem=offline_item, option="기본"
                    )

                    # 데이터 병합
                    online_variant.stock_quantity = (
                        online_variant.stock_quantity or 0
                    ) + (offline_variant.stock_quantity or 0)
                    online_variant.sales_quantity = (
                        online_variant.sales_quantity or 0
                    ) + (offline_variant.sales_quantity or 0)

                    if offline_variant.price:
                        online_variant.price = offline_variant.price
                    if offline_variant.cost_price:
                        online_variant.cost_price = offline_variant.cost_price
                    if offline_variant.sale_price:
                        online_variant.sale_price = offline_variant.sale_price

                    # 상품명 변경
                    online_product = online_variant.product
                    offline_item_name = offline_item.name
                    online_product.name = offline_item_name
                    online_product.save()
                    online_variant.save()

                    # 오프라인 데이터 정리
                    offline_product = offline_variant.product
                    offline_variant.delete()
                    offline_item.delete()

                    if not offline_product.variants.exists():
                        offline_product.delete()

                    results["success"].append(
                        {
                            "management_code": code,
                            "product_name": offline_item_name,
                            "message": "병합 완료",
                        }
                    )

            except Exception as e:
                results["failed"].append({"management_code": code, "error": str(e)})

        return Response(
            {
                "results": results,
                "total_success": len(results["success"]),
                "total_failed": len(results["failed"]),
            },
            status=status.HTTP_200_OK,
        )
