from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import MultiPartParser
from django.db import transaction
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant
from .serializers import ProductOptionSerializer, ProductVariantSerializer, ProductVariantFullUpdateSerializer, InventoryItemWithVariantsSerializer, ProductVariantCreateSerializer
import pandas as pd

# 빠른 값 조회용 엔드포인트
class ProductOptionListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 옵션 리스트 조회",
        operation_description="상품 드롭다운용으로 product_id와 name만 간단히 반환합니다.",
        responses={200: ProductOptionSerializer(many=True)}
    )
    def get(self, request):
        products = InventoryItem.objects.all().only('product_id', 'name')
        serializer = ProductOptionSerializer(products, many=True)
        return Response(serializer.data)
    
# 재고 전체 조회
class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

    permission_classes = [AllowAny]
    # 전체 목록 조회

    @swagger_auto_schema(
        operation_summary="전체 제품 목록 조회 (방패필통)",
        operation_description="현재 등록된 모든 제품 목록을 조회합니다.",
        responses={200: InventoryItemWithVariantsSerializer(many=True)}
    )
    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemWithVariantsSerializer(items, many=True)
        return Response(serializer.data)


# 일부 조회
class InventoryItemView(APIView):
    '''
    GET: 특정 상품 기본 정보 조회 (상품코드, 상품명, 생성일자)
    '''
    permission_classes = [AllowAny]

    # 상품 기본 정보 조회
    @swagger_auto_schema(
        operation_summary="특정 상품 상세 정보 조회 (방패필통)",
        operation_description="product_id에 해당하는 상품의 기본 정보와 연결된 상세 상품 목록까지 함께 조회합니다.",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_STRING
        )],
        responses={200: InventoryItemWithVariantsSerializer, 404: "Not Found"}
    )
    def get(self, request, product_id: str):
        try:
            item = InventoryItem.objects.get(product_id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InventoryItemWithVariantsSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

# 상품 csv 업로드 Create

class ProductVariantCSVUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]

    def generate_variant_code(self, base_code):
        existing = ProductVariant.objects.filter(variant_code__startswith=base_code).values_list("variant_code", flat=True)
        suffix = ord("A")
        while True:
            candidate = f"{base_code}000{chr(suffix)}"
            if candidate not in existing:
                return candidate
            suffix += 1

    @swagger_auto_schema(
        operation_summary="상품 XLSX 일괄 업로드",
        operation_description="엑셀 파일을 업로드하여 상품 및 상세 품목 정보를 일괄 생성 또는 업데이트합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 XLSX 파일"
            )
        ],
        responses={200: "성공", 400: "파일 에러 또는 유효성 오류"}
    )
    def post(self, request):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response({"error": "파일이 첨부되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            return Response({"error": f"엑셀 파일을 읽을 수 없습니다: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        required_cols = ["상품코드", "상품명", "상품 품목코드", "옵션", "판매가", "재고", "판매수량", "환불수량"]
        for col in required_cols:
            if col not in df.columns:
                return Response({"error": f"필수 컬럼이 누락되었습니다: {col}"}, status=status.HTTP_400_BAD_REQUEST)

        created, updated, errors = [], [], []

        with transaction.atomic():
            for i, row in df.iterrows():
                try:
                    product_id = str(row["상품코드"]).strip()
                    product_name = str(row["상품명"]).strip()
                    option = str(row["옵션"]).strip() if pd.notnull(row["옵션"]) else "기본"
                    if not option:
                        option = "기본"

                    raw_code = row["상품 품목코드"]
                    variant_code = str(raw_code).strip() if pd.notna(raw_code) and str(raw_code).strip() not in ["", "-"] else self.generate_variant_code(product_id)

                    price = int(row["판매가"]) if pd.notnull(row["판매가"]) else 0
                    delta_stock = int(row["재고"]) if pd.notnull(row["재고"]) else 0
                    delta_order = int(row["판매수량"]) if pd.notnull(row["판매수량"]) else 0
                    delta_return = int(row["환불수량"]) if pd.notnull(row["환불수량"]) else 0

                    # 상품 생성 또는 가져오기
                    product, _ = InventoryItem.objects.get_or_create(
                        product_id=product_id,
                        defaults={"name": product_name}
                    )

                    # 품목 생성 or 업데이트
                    if option == "기본":
                        variant = ProductVariant.objects.filter(product=product, option="기본").first()
                    else:
                        variant = ProductVariant.objects.filter(variant_code=variant_code).first()


                    if variant:
                        # 업데이트
                        variant.option = option
                        variant.price = price
                        variant.stock += delta_stock
                        variant.order_count += delta_order
                        variant.return_count += delta_return
                        variant.save()
                        updated.append(ProductVariantSerializer(variant).data)
                    else:
                        # 생성
                        variant = ProductVariant.objects.create(
                            product=product,
                            variant_code=variant_code,
                            option=option,
                            price=price,
                            stock=delta_stock,
                            order_count=delta_order,
                            return_count=delta_return
                        )
                        created.append(ProductVariantSerializer(variant).data)

                except Exception as e:
                    errors.append(f"{i+2}행: {str(e)}")

        return Response({
            "created_count": len(created),
            "updated_count": len(updated),
            "created": created,
            "updated": updated,
            "errors": errors
        }, status=status.HTTP_200_OK)

# 상품 상세 정보 Create
class ProductVariantCreateView(APIView):
    permission_classes = [AllowAny]

    def generate_variant_code(self, base_code):
        existing_codes = ProductVariant.objects.filter(
            variant_code__startswith=base_code
        ).values_list('variant_code', flat=True)

        suffix_char = ord("A")
        while True:
            candidate = f"{base_code}000{chr(suffix_char)}"
            if candidate not in existing_codes:
                return candidate
            suffix_char += 1

    @swagger_auto_schema(
        operation_summary="상품 상세 정보 생성 (방패 필통 크림슨)",
        operation_description="기존 product_id가 있으면 연결하고, 없으면 새로 생성한 뒤 variant_code 자동 생성",
        request_body=ProductVariantCreateSerializer,
        responses={201: ProductVariantSerializer, 400: "Bad Request"}
    )
    def post(self, request):
        product_id = request.data.get('product_id')
        product_name = request.data.get('name')

        if not product_id or not product_name:
            return Response({"error": "product_id와 name은 필수입니다."}, status=status.HTTP_400_BAD_REQUEST)

        product, _ = InventoryItem.objects.get_or_create(
            product_id=product_id,
            defaults={'name': product_name}
        )

        variant_code = self.generate_variant_code(product)

        serializer = ProductVariantFullUpdateSerializer(
            data=request.data,
            context={'product': product, 'request': request}
        )
        if serializer.is_valid():
            serializer.save(variant_code=variant_code)
            return Response(ProductVariantSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ProductVariantDetailView(APIView):
    """
    GET / PATCH / DELETE: 특정 상품의 상세 정보 접근
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 조회 (방패필통 크림슨)",
        manual_parameters=[
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                description="조회할 variant_code (예: P00000XN000A)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={200: ProductVariantSerializer, 404: "Not Found"}
    )
    def get(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.filter(variant_code=variant_code, is_active=True).first()
            if not variant:
                return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_summary="세부 품목 정보 수정 (방패필통 크림슨)",
        manual_parameters=[
        openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                description="수정할 variant_code (예: P00000XN000A)",
                type=openapi.TYPE_STRING
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["product_id", "name", "option", "stock", "price"],
            properties={
                "product_id": openapi.Schema(type=openapi.TYPE_STRING, example="P00000YC"),
                "name": openapi.Schema(type=openapi.TYPE_STRING, example="방패 필통"),
                "option": openapi.Schema(type=openapi.TYPE_STRING, example="색상 : 크림슨"),
                "stock": openapi.Schema(type=openapi.TYPE_INTEGER, example=100),
                "price": openapi.Schema(type=openapi.TYPE_INTEGER, example=5000),
                "min_stock": openapi.Schema(type=openapi.TYPE_INTEGER, example=4),
                "description": openapi.Schema(type=openapi.TYPE_STRING, example=""),
                "memo": openapi.Schema(type=openapi.TYPE_STRING, example=""),
                "suppliers": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "name": openapi.Schema(type=openapi.TYPE_STRING, example="넥스트물류"),
                            "cost_price": openapi.Schema(type=openapi.TYPE_INTEGER, example=3016),
                            "is_primary": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        }
                    )
                )
            }
        ),
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def patch(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantFullUpdateSerializer(variant, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(ProductVariantSerializer(serializer.instance).data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 삭제 (방패필통 크림슨)",
        manual_parameters=[
            openapi.Parameter(
                name="variant_code",
                in_=openapi.IN_PATH,
                description="삭제할 variant_code (예: P00000XN000A)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={204: "삭제 완료", 404: "Not Found"}
    )
    def delete(self, request, variant_code: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        variant.is_active = False
        variant.save()
        return Response(status=204)