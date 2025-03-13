from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant
from .serializers import InventoryItemSerializer, ProductVariantSerializer


class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

    permission_classes = [AllowAny]  # 테스트용 jwt면제

    @swagger_auto_schema(
        operation_summary="전체 제품 목록 조회",
        operation_description="현재 등록된 모든 제품 목록을 조회합니다.",
        responses={200: InventoryItemSerializer(many=True)}
    )
    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemSerializer(items, many=True)
        return Response(serializer.data)

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


class ProductVariantDetailView(APIView):
    """
    GET: 특정 제품의 상세 정보 조회
    PUT: 특정 제품  정보 수정
    DELETE: 특정 제품 정보 삭제
    """

    permission_classes = [AllowAny]

    # 제품 정보 조회회
    @swagger_auto_schema(operation_summary="특정 품목의 정보 상세 조회",
                         operation_description="URL 파라미터로 전달된 variant_id에 해당하는 특정 제품의 정보를 조회합니다.",
                         manual_parameters=[
                             openapi.Parameter(
                                 name="variant_id",
                                 in_=openapi.IN_PATH,
                                 description="조회할 제품의 variant_id",
                                 type=openapi.TYPE_INTEGER
                             )
                         ],
                         responses={200: ProductVariantSerializer, 404: "Not Found"})
    def get(self, request, variant_id: int):
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 제품 정보 수정정
    @swagger_auto_schema(
        operation_summary="특정 품목 정보 수정",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 특정 제품의 상세 정보를 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 제품의 variant_id",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=ProductVariantSerializer,
        responses={200: ProductVariantSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, variant_id: int):
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(variant, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # patch를 이용한 제품 정보 수정정
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

    # 품목 정보 삭제

    @swagger_auto_schema(
        operation_summary="특정 품목 정보 삭제",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 품목 정보를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="삭제할 품목목의 vriant_ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={204: "No Content: Successfully Deleted", 404: "Not Found"}
    )
    def delete(self, request, variant_id: int):
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
