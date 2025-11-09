from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404

from apps.supplier.models import Supplier
from apps.orders.models import Order
from apps.supplier.serializers import SupplierSerializer, SupplierOptionSerializer, SupplierOrderSerializer

class SupplierListCreateView(APIView):
    permission_classes = [AllowAny]
    """
    GET: 모든 공급업체 목록 조회
    POST: 새로운 공급업체 등록
    """

    @swagger_auto_schema(
        operation_summary="공급업체 목록 조회",
        responses={200: SupplierSerializer(many=True)}
    )
    def get(self, request):
        suppliers = Supplier.objects.all()
        serializer = SupplierSerializer(suppliers, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="공급업체 등록",
        request_body=SupplierSerializer,
        responses={201: SupplierSerializer}
    )
    def post(self, request):
        serializer = SupplierSerializer(data=request.data)
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
    
class SupplierOrderDetailView(APIView):
    """
    특정 공급업체의 발주 세부내역 조회 (품목, 단가, 수량, 총액 등)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="공급업체별 발주 내역 상세 조회",
        operation_description="공급업체별로 발주(주문) 및 그 안의 품목, 가격, 수량 등의 세부 정보를 조회합니다.",
        responses={200: SupplierOrderSerializer(many=True)}
    )
    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        orders = (
            Order.objects.filter(supplier=supplier)
            .prefetch_related("items__variant__product")
            .order_by("-order_date")
        )

        serializer = SupplierOrderSerializer(orders, many=True)
        return Response({
            "supplier": supplier.name,
            "orders": serializer.data
        }, status=status.HTTP_200_OK)
