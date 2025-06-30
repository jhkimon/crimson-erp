from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant
from .serializers import ProductVariantSerializer, ProductVariantFullUpdateSerializer, InventoryItemWithVariantsSerializer, ProductVariantCreateSerializer

# 재고 전체 조회
class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

    permission_classes = [AllowAny]
    # 전체 목록 조회

    @swagger_auto_schema(
        operation_summary="전체 제품 목록 조회 (갤럭시 S24 Ultra)",
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
        operation_summary="특정 상품 상세 정보 조회 (갤럭시 S24 Ultra)",
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

# 상품 상세 정보 Create
class ProductVariantCreateView(APIView):
    permission_classes = [AllowAny]

    def generate_variant_code(self, product):
        base_code = product.product_id
        existing_codes = ProductVariant.objects.filter(product=product).values_list('variant_code', flat=True)
        suffixes = [int(code.split('-')[-1]) for code in existing_codes if '-' in code and code.split('-')[-1].isdigit()]
        next_suffix = max(suffixes, default=0) + 1
        return f"{base_code}-{next_suffix:02d}"

    @swagger_auto_schema(
        operation_summary="상품 상세 정보 생성 (갤럭시 S24 Ultra 실버)",
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
    GET / PUT / DELETE: 특정 상품의 상세 정보 접근
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 조회 (갤럭시 S24 Ultra 실버)",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="조회할 variant_code (예: P1001-01)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={200: ProductVariantSerializer, 404: "Not Found"}
    )
    def get(self, request, variant_id: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 수정 (갤럭시 S24 Ultra 실버)",
        request_body=ProductVariantCreateSerializer,
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def patch(self, request, variant_id: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        serializer = ProductVariantFullUpdateSerializer(variant, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(ProductVariantSerializer(serializer.instance).data)
        return Response(serializer.errors, status=400)

    @swagger_auto_schema(
        operation_summary="세부 품목 정보 삭제 (갤럭시 S24 Ultra 실버)",
        responses={204: "삭제 완료", 404: "Not Found"}
    )
    def delete(self, request, variant_id: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=404)

        variant.delete()
        return Response(status=204)