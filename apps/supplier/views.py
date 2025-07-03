from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.supplier.models import Supplier
from apps.supplier.serializers import SupplierSerializer, SupplierOptionSerializer

class SupplierListCreateView(APIView):
    permission_classes = [AllowAny]
    """
    GET: 모든 공급업체 목록 조회
    POST: 새로운 공급업체 등록
    PATCH: 공급업체 정보 변경
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
    
    @swagger_auto_schema(
            operation_summary="공급업체 정보 수정",
            request_body=SupplierOptionSerializer,
            responses={200: SupplierOptionSerializer}
    )
    def patch(self, request, pk):
        try:
            supplier = Supplier.objects.get(pk=pk)
        except Supplier.DoesNotExist:
            return Response({'detail': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupplierOptionSerializer(supplier, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SupplierRetrieveUpdateView(APIView):
    permission_classes = [AllowAny]
    """
    GET: 특정 공급업체 상세 조회
    """

    @swagger_auto_schema(
        operation_summary="공급업체 상세 조회",
        responses={200: SupplierSerializer}
    )
    def get(self, request, pk):
        try:
            supplier = Supplier.objects.get(pk=pk)
        except Supplier.DoesNotExist:
            return Response({'detail': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupplierSerializer(supplier)
        return Response(serializer.data)