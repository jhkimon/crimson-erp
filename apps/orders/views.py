# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .serializers import OrderSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class OrderListView(APIView):
    @swagger_auto_schema(
        operation_description="Get a list of all orders",
        responses={200: OrderSerializer(many=True)}
    )
    def get(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Create a new order",
        request_body=OrderSerializer,
        responses={201: OrderSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else: 
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class OrderDetailView(APIView):
    def get_object(self, order_id):
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_description="Get details of a specific order",
        manual_parameters=[
            openapi.Parameter(
                'order_id', 
                openapi.IN_PATH,
                description="ID of the order to retrieve",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: OrderSerializer,
            404: openapi.Response(description="Order not found")
        }
    )
    def get(self, request, order_id):
        order = self.get_object(order_id)
        if not order:
            return Response(
                {"error": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Delete a specific order",
        manual_parameters=[
            openapi.Parameter(
                'order_id', 
                openapi.IN_PATH,
                description="ID of the order to delete",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            204: openapi.Response(description="Order deleted successfully"),
            404: openapi.Response(description="Order not found")
        }
    )
    def delete(self, request, order_id):
        order = self.get_object(order_id)
        if not order:
            return Response(
                {"error": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        order.delete()
        return Response(
            {"message": "Order deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )

class OrderStatusView(APIView):
    def get_object(self, order_id):
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Update the status (and optionally the quantity) of a specific order",
        manual_parameters=[
            openapi.Parameter(
                'order_id', 
                openapi.IN_PATH,
                description="ID of the order to update",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="New status for the order"
                ),
                'quantity': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="New quantity for the order"
                ),
            }
        ),
        responses={
            200: OrderSerializer,
            400: openapi.Response(description="Status field is required"),
            404: openapi.Response(description="Order not found")
        }
    )
    def patch(self, request, order_id):
        try:
            # Convert order_id to integer
            order_id = int(order_id)
        except ValueError:
            return Response(
                {"error": "Order ID must be an integer"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        order = self.get_object(order_id)
        if not order:
            return Response(
                {"error": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if 'status' is in the request data
        if 'status' in request.data:
            order.status = request.data['status']

        # Check if 'quantity' is in the request data and convert it to an integer
        if 'quantity' in request.data:
            try:
                order.quantity = int(request.data['quantity'])  # Force conversion to integer
            except ValueError:
                return Response(
                    {"error": "Quantity must be an integer"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        order.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
