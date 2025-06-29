from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.supplier.models import Supplier
from apps.supplier.serializers import SupplierSerializer


class SupplierListCreateView(APIView):
    """
    GET: 모든 공급업체 목록 조회
    POST: 새로운 공급업체 등록 (공급하는 variant_code 리스트 포함)
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
    """
    GET: 특정 공급업체 상세 조회
    PUT: 특정 공급업체 정보 및 variant_code 갱신
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

    @swagger_auto_schema(
        operation_summary="공급업체 정보 수정",
        request_body=SupplierSerializer,
        responses={200: SupplierSerializer}
    )
    def put(self, request, pk):
        try:
            supplier = Supplier.objects.get(pk=pk)
        except Supplier.DoesNotExist:
            return Response({'detail': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupplierSerializer(supplier, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)