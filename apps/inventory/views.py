from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant
from .serializers import ProductVariantSerializer, ProductVariantCRUDSerializer, InventoryItemWithVariantsSerializer

# 재고 전체 조회
class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

    permission_classes = [AllowAny]  # 테스트용 jwt면제
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



# 상품 상세 정보 CRUD
class ProductVariantDetailView(APIView):
    """
    POST: 특정 상품의 상세 정보 생성 (variant_code)
    GET: 특정 상품의 상세 정보 조회 (variant_code)
    PUT: 특정 상품의 상세 정보 수정 (variant_code)
    DELETE: 특정 상품의 상세 정보 삭제 (variant_code)
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 생성 (갤럭시 S24 Ultra, 그린)",
        operation_description="variant_code를 통해 새로운 상세 정보를 생성합니다.",
        request_body=ProductVariantCRUDSerializer,
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="생성할 variant_code (ex: P1001-01)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={201: ProductVariantSerializer, 400: "Bad Request"}
    )
    def post(self, request, variant_id: str):
        # variant_code가 중복되면 400 반환
        if ProductVariant.objects.filter(variant_code=variant_id).exists():
            return Response({"error": "이미 존재하는 variant_code 입니다."}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product_id')
        if not product_id:
            return Response({"error": "product_id가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = InventoryItem.objects.get(product_id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "상품 기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantCRUDSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(product=product, variant_code=variant_id)
            return Response(ProductVariantSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="특정 세부 품목 정보 조회 (갤럭시 S24 Ultra, 그린)",
        operation_description="variant_code를 통해 해당 세부 품목 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="조회할 variant_code (ex: P1001-01)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={200: ProductVariantSerializer, 404: "Not Found"}
    )
    def get(self, request, variant_id: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 수정 (갤럭시 S24 Ultra, 그린)",
        operation_description="variant_code를 통해 해당 세부 품목 정보를 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 variant_code (ex: P1001-01)",
                type=openapi.TYPE_STRING
            )
        ],
        request_body=ProductVariantCRUDSerializer,
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, variant_id: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(variant, data=request.data, partial=False, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 삭제 (갤럭시 S24 Ultra, 그린)",
        operation_description="variant_code를 통해 해당 세부 품목 정보를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="삭제할 variant_code (ex: P1001-01)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={204: "삭제 완료", 404: "Not Found"}
    )
    def delete(self, request, variant_id: str):
        try:
            variant = ProductVariant.objects.get(variant_code=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)