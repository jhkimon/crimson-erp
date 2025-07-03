from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Order
from .serializers import OrderWriteSerializer, OrderReadSerializer, OrderCompactSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class OrderListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="전체 주문 보기",
        operation_description="Get a list of all orders in the system.",
        responses={200: OrderCompactSerializer(many=True)}
    )
    def get(self, request):
        orders = Order.objects.all()
        serializer = OrderCompactSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="주문 생성하기",
        operation_description="Submit a new order with required fields.",
        request_body=OrderWriteSerializer,
        responses={201: OrderReadSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = OrderWriteSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            # 응답은 읽기용으로 직렬화
            read_serializer = OrderReadSerializer(order)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, order_id):
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_summary="주문 상세 보기",
        operation_description="Retrieve detailed information about a specific order.",
        responses={200: OrderReadSerializer, 404: "Not Found"}
    )
    def get(self, request, order_id):
        order = self.get_object(order_id)
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderReadSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="주문 삭제하기",
        operation_description="Delete a specific order by its ID.",
        responses={204: "No Content", 404: "Not Found"}
    )
    def delete(self, request, order_id):
        order = self.get_object(order_id)
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        order.delete()
        return Response({"message": "Order deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="주문 상태 변경하기",
        operation_description="Update the status of a specific order.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={200: OrderReadSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def patch(self, request, order_id):
        order = self.get_object(order_id)
        if not order:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        status_val = request.data.get('status')
        if not status_val:
            return Response({"error": "Missing 'status'"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = status_val
        order.save()
        serializer = OrderReadSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)