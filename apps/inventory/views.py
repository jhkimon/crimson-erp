from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant
from .serializers import InventoryItemSerializer, ProductVariantSerializer, ProductVariantCRUDSerializer, InventoryItemWithVariantsSerializer

# 재고 전체 목록 작업 (조회 및 추가)


class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

    permission_classes = [AllowAny]  # 테스트용 jwt면제
    # 전체 목록 조회

    @swagger_auto_schema(
        operation_summary="전체 제품 목록 조회",
        operation_description="현재 등록된 모든 제품 목록을 조회합니다.",
        responses={200: InventoryItemWithVariantsSerializer(many=True)}
    )
    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemWithVariantsSerializer(items, many=True)
        return Response(serializer.data)

    # 신규 상품 추가
    @swagger_auto_schema(
        operation_summary="새로운 제품 추가",
        operation_description="새로운 제품을 등록합니다.",
        request_body=InventoryItemSerializer,
        responses={201: InventoryItemSerializer}
    )
    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 개별 제품 관련 작업 (조회/수정/삭제)


class InventoryItemView(APIView):
    '''
    GET: 특정 상품 기본 정보 조회 (상품코드, 상품명, 생성일자)
    PUT: 상품 기본 정보 수정
    DELETE: 상품 삭제
    '''
    permission_classes = [AllowAny]

    # 상품 기본 정보 조회
    @swagger_auto_schema(
        operation_summary="특정 상품 기본 정보 및 상세 목록 조회",
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

    # 상품 기본 정보 수정
    @swagger_auto_schema(
        operation_summary="특정 상품 기본 정보 수정",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품의 기본 정보를 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="수정할 상품의 product_id",
                type=openapi.TYPE_STRING
            )
        ],
        request_body=InventoryItemSerializer,
        responses={200: InventoryItemSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, product_id: str):
        try:
            item = InventoryItem.objects.get(product_id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InventoryItemSerializer(item, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="특정 상품 삭제",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품을 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="삭제할 상품의 product_id",
                type=openapi.TYPE_STRING
            )
        ],
        responses={204: "삭제 완료: Successfully Deleted", 404: "Not Found"}
    )
    def delete(self, request, product_id: str):
        try:
            item = InventoryItem.objects.get(product_id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 상품 상세 정보 CRUD
class ProductVariantCreateView(APIView):
    """
    POST: 특정 상품의 상세 정보 생성
    """
    permission_classes = [AllowAny]
    # 상품 상세 정보 추가
    @swagger_auto_schema(
        operation_summary="특정 상품에 새로운 상세 정보 추가",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품에 상세 정보를 생성합니다.",
        request_body=ProductVariantCRUDSerializer,
        responses={201: ProductVariantSerializer, 400: "Bad Request"}
    )
    def post(self, request, product_id: str):
        try:
            product = InventoryItem.objects.get(product_id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "상품 기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantCRUDSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(ProductVariantSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductVariantDetailView(APIView):
    """
    GET: 특정 상품의 상세 정보 조회 (상세코드, 옵션, 재고량, 가격, 생성일자, 수정일자)
    PUT: 특정 상품 상세 정보 수정
    DELETE: 특정 상품 상세 정보 삭제
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="특정 세부 품목 정보 조회",
        operation_description="variant_code를 통해 해당 세부 품목 정보를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="조회할 variant_code",
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
        operation_summary="특정 상품의 상세 정보 수정",
        operation_description="variant_code를 통해 해당 세부 품목 정보를 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 variant_code",
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
        operation_summary="특정 상품의 상세 정보 삭제",
        operation_description="variant_code를 통해 해당 세부 품목 정보를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="삭제할 variant_code",
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