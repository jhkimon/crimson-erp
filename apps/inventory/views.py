from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem
from .serializers import InventoryItemSerializer

class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

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