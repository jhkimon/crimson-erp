from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant
from .serializers import InventoryItemSerializer, ProductVariantSerializer

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
        responses={200: InventoryItemSerializer(many=True)}
    )
    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemSerializer(items, many=True)
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
        operation_summary="특정 상품 기본 정보 조회",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품의 기본 정보를 조회합니다",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_INTEGER
        )],
        responses={200: InventoryItemSerializer, 404: "Not Found"})
    def get(self, request, product_id: int):
        try:
            item = InventoryItem.objects.get(id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InventoryItemSerializer(item)
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
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=InventoryItemSerializer,
        responses={200: InventoryItemSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, product_id: int):
        try:
            item = InventoryItem.objects.get(id=product_id)
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
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={204: "삭제 완료: Successfully Deleted", 404: "Not Found"}
    )
    def delete(self, request, product_id: int):
        try:
            item = InventoryItem.objects.get(id=product_id)
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
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품의 상세 정보를 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="상세 정보를 추가할 상품의 product_id",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=ProductVariantSerializer,
        responses={201: ProductVariantSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def post(self, request, product_id: int):
        try:
            product = InventoryItem.objects.get(id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "상품 기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(
            data=request.data, context={'request': request, 'product': product})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductVariantDetailView(APIView):
    """
    GET: 특정 상품의 상세 정보 조회 (상세코드, 옵션, 재고량, 가격, 생성일자, 수정일자자)
    PUT: 특정 상품 상세 정보 수정
    DELETE: 특정 상품 상세 정보 삭제
    """

    permission_classes = [AllowAny]

    # 제품 상세 정보 조회

    @swagger_auto_schema(operation_summary="특정 상품의 상세 정보 조회",
                         operation_description="URL 파라미터로 전달된 variant_id에 해당하는 특정 상품의 상세 정보를 조회합니다.",
                         manual_parameters=[openapi.Parameter(
                             name="product_id",
                             in_=openapi.IN_PATH,
                             description="조회할 상품의 product_id",
                             type=openapi.TYPE_INTEGER
                         ),
                             openapi.Parameter(
                                 name="variant_id",
                                 in_=openapi.IN_PATH,
                                 description="조회할 상품의 variant_id",
                                 type=openapi.TYPE_INTEGER
                         )
                         ],
                         responses={200: ProductVariantSerializer, 404: "Not Found"})
    def get(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 제품 상세 정보 수정
    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 수정",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 특정 상품의 상세 정보를 수정합니다.",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_INTEGER
        ),
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 상품의 variant_id",
                type=openapi.TYPE_INTEGER
        )
        ],
        request_body=ProductVariantSerializer,
        responses={200: ProductVariantSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(
            variant, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # patch를 이용한 제품 정보 수정
    ''' 
    @swagger_auto_schema(
        operation_summary="특정 품목 부분 수정",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 제품 변형 정보를 부분적으로 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 제품 변형(variant)의 ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=ProductVariantSerializer,
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def patch(self, request, variant_id: int):
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # partial=True를 통해 부분 업데이트를 허용합니다.
        serializer = ProductVariantSerializer(variant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    '''

    # 상품 상세 정보 삭제

    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 삭제",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 상품의 상세세 정보를 삭제합니다.",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_INTEGER
        ),
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="삭제할 상품의 variant_id",
                type=openapi.TYPE_INTEGER
        )
        ],
        responses={204: "삭제 완료: Successfully Deleted", 404: "Not Found"}
    )
    def delete(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다"}, status=status.HTTP_404_NOT_FOUND)

        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InventoryItemMergeView(APIView):
    """
    POST: 동일 상품이지만 id가 다른 상품을 하나로 병합용
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 코드 병합",
        operation_description="여러 상품(source_ids)을 target_id로 병합합니다. 병합된 상품은 is_active=False 처리됩니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["target_id", "source_ids"],
            properties={
                "target_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="최종 남길 상품의 ID"),
                "source_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description="합칠(비활성 처리할) 상품 ID 리스트"
                )
            }
        ),
        responses={204: "Merge completed.",
                   400: "Bad Request", 404: "Not Found"}
    )
    def post(self, request):
        target_id = request.data.get("target_id")  # 병합 대상 상품 id (최종적으로 남는 id)
        # 병합 필요 상품 id (fade out되는 id)
        source_ids = request.data.get("source_ids")

        if not isinstance(source_ids, list) or not target_id:
            return Response({"error": "target_id와 source_ids(리스트)를 모두 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure target exists
        try:
            target = InventoryItem.objects.get(id=target_id, is_active=True)
        except InventoryItem.DoesNotExist:
            return Response({"error": "target_id에 해당하는 상품이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        # Exclude target from sources if accidentally included
        source_ids = [sid for sid in source_ids if sid != target_id]
        sources = InventoryItem.objects.filter(
            id__in=source_ids, is_active=True)
        if not sources:
            return Response({"error": "합칠 source_ids에 유효한 상품이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # Execute merge within transaction
        with transaction.atomic():
            # 1) Move all variants of source items to target
            ProductVariant.objects.filter(product_id__in=[s.id for s in sources])\
                .update(product=target)
            # 2) Soft-delete source items
            sources.update(is_active=False)

        return Response(status=status.HTTP_204_NO_CONTENT)
