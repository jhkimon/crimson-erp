from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404

from apps.supplier.models import Supplier, SupplierVariant
from apps.inventory.models import ProductVariant
from apps.supplier.serializers import SupplierSerializer, SupplierOptionSerializer, SupplierVariantUpdateTableSerializer

class SupplierListCreateView(APIView):
    permission_classes = [AllowAny]
    """
    GET: 모든 공급업체 목록 조회
    POST: 새로운 공급업체 등록
    """

    @swagger_auto_schema(
        operation_summary="공급업체 목록 조회",
        responses={200: SupplierOptionSerializer(many=True)}
    )
    def get(self, request):
        suppliers = Supplier.objects.all()
        serializer = SupplierOptionSerializer(suppliers, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="공급업체 등록",
        request_body=SupplierOptionSerializer,
        responses={201: SupplierOptionSerializer}
    )
    def post(self, request):
        serializer = SupplierOptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplierRetrieveUpdateView(APIView):
    permission_classes = [AllowAny]
    """
    GET: 특정 공급업체 상세 조회
    PATCH: 특정 공급업체 정보 수정
    """

    @swagger_auto_schema(
        operation_summary="공급업체 상세 조회",
        responses={200: SupplierSerializer}
    )
    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        serializer = SupplierSerializer(supplier)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="공급업체 정보 수정",
        request_body=SupplierOptionSerializer,
        responses={200: SupplierSerializer}
    )
    def patch(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        serializer = SupplierSerializer(supplier, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SupplierVariantUpdateView(APIView):
    @swagger_auto_schema(
        operation_summary="공급업체-상품 옵션 매핑 수정",
        manual_parameters=[
            openapi.Parameter(
                'supplier_id',
                openapi.IN_PATH,
                description="공급업체 ID (예: 1)",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'variant_code',
                openapi.IN_PATH,
                description="상품 상세 코드 (예: P00000XN000A)",
                type=openapi.TYPE_STRING
            ),
        ],
        request_body=SupplierVariantUpdateTableSerializer,
        responses={200: SupplierVariantUpdateTableSerializer}
    )
    def patch(self, request, supplier_id, variant_code):
        # 1. variant_code로 ProductVariant 객체 찾기
        variant = get_object_or_404(ProductVariant, variant_code=variant_code)

        # 2. supplier_id와 variant를 기준으로 SupplierVariant 조회
        sv = get_object_or_404(SupplierVariant, supplier_id=supplier_id, variant=variant)

        # 3. 수정 로직
        serializer = SupplierVariantUpdateTableSerializer(sv, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)