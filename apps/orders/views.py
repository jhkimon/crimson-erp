from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
from django.core.paginator import Paginator
from apps.orders.filters import OrderFilter
from rest_framework import status
from apps.orders.models import Order, OrderItem
from apps.inventory.models import ProductVariant
from .serializers import OrderWriteSerializer, OrderReadSerializer, OrderCompactSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from apps.utils.email_utils import send_order_created_email, send_order_approved_email

class OrderListView(APIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ['order_date', 'expected_delivery_date'] 

    @swagger_auto_schema(
            operation_summary="전체 주문 보기",
            operation_description="필터링, 정렬, 페이지네이션이 가능한 주문 리스트",
            manual_parameters=[
                openapi.Parameter('ordering', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='정렬 필드 (order_date, expected_delivery_date)'),
                openapi.Parameter('product_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='상품명'),
                openapi.Parameter('supplier', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='공급업체 이름'),
                openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='주문 상태'),
                openapi.Parameter('start_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date', description='조회 시작일 (예: 2025-07-01)'),
                openapi.Parameter('end_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date',  description='조회 종료일 (예: 2025-08-01)'),
                openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='페이지 번호 (default: 1)'),
            ],
            responses={200: OrderCompactSerializer(many=True)}
        )
    
    def get(self, request):
        queryset = Order.objects.prefetch_related("items__variant__product").all()

        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)

        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(queryset, request, view=self)

        serializer = OrderCompactSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_summary="주문 생성하기",
        operation_description="주문을 생성합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["supplier", "manager_name", "order_date", "expected_delivery_date", "status", "items"],
            properties={
                "supplier": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                "manager_name": openapi.Schema(type=openapi.TYPE_STRING, example="유시진"),
                "order_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", example="2025-07-07"),
                "expected_delivery_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", example="2025-07-09"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, example="PENDING"),
                "instruction_note": openapi.Schema(type=openapi.TYPE_STRING, example="납품 전에 전화주세요"),
                "note": openapi.Schema(type=openapi.TYPE_STRING, example="발주 요청"),
                "vat_included": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                "packaging_included": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                "items": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "variant_code": openapi.Schema(type=openapi.TYPE_STRING, example="P00000XN000A"),
                            "quantity": openapi.Schema(type=openapi.TYPE_INTEGER, example=100),
                            "unit_price": openapi.Schema(type=openapi.TYPE_INTEGER, example=5000),
                            "remark": openapi.Schema(type=openapi.TYPE_STRING, example="박스 포장"),
                            "spec": openapi.Schema(type=openapi.TYPE_STRING, example="B급")
                        }
                    )
                )
            }
        ),
        responses={201: OrderReadSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = OrderWriteSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            # 응답은 읽기용으로 직렬화
            read_serializer = OrderReadSerializer(order)
            send_order_created_email(order)
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

    def get_object(self, order_id):
            try:
                return Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return None

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

        new_status = request.data.get('status')
        if not new_status:
            return Response({"error": "Missing 'status'"}, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({
                "error": f"'{new_status}'는 유효하지 않은 상태입니다.",
                "valid_choices": valid_statuses
            }, status=status.HTTP_400_BAD_REQUEST)
        
        previous_status = order.status
        order.status = new_status
        order.save()

        # 이전 상태와 동일
        if previous_status == new_status:
            return Response({
                "error": "이미 동일한 상태입니다. 상태를 변경하려면 다른 값을 입력하세요.",
                "status": new_status
            }, status=status.HTTP_400_BAD_REQUEST)
        

        # APPROVED 로 변경시.
        if previous_status != "APPROVED" and new_status == "APPROVED":
            send_order_approved_email(order)
    

        # 완료 X -> COMPLETED (재고 증가)
        if previous_status != "COMPLETED" and new_status == "COMPLETED":
            for item in order.items.all():
                variant = item.variant
                if variant:
                    variant.stock = variant.stock + item.quantity
                    variant.save()

        # COMPLETED -> CANCELLED or APPROVED 변경 (재고 감소)
        elif previous_status == "COMPLETED" and new_status != "COMPLETED":
            for item in order.items.all():
                variant = item.variant
                if variant:
                    if variant.stock < item.quantity:
                        return Response({
                            "error": "현재 재고가 부족하여 상태 변경이 불가능합니다.",
                            "item": {
                                "variant_code": variant.variant_code,
                                "name": variant.product.name if variant.product else None,
                                "option": variant.option if variant.option else None,
                                "current_stock": variant.stock,
                                "required_quantity": item.quantity,
                                "remaining_stock_if_changed": variant.stock - item.quantity
                            }
                        }, status=status.HTTP_400_BAD_REQUEST)
                    variant.stock -= item.quantity
                    variant.save()

        serializer = OrderReadSerializer(order)
        # 재고 변경 체크
        stock_changes = []
        for item in order.items.all():
            variant = item.variant
            if variant:
                change = item.quantity
                if previous_status != "COMPLETED" and new_status == "COMPLETED":
                    before = variant.stock - change
                elif previous_status == "COMPLETED" and new_status != "COMPLETED":
                    before = variant.stock + change
                else:
                    before = variant.stock
                stock_changes.append({
                    "variant_code": variant.variant_code,
                    "name": variant.product.name if variant.product else None,
                    "option": variant.option if variant.option else None,
                    "quantity": change,
                    "stock_before": before,
                    "stock_after": variant.stock
                })

        return Response({
            "order": serializer.data,
            "stock_changes": stock_changes
        }, status=status.HTTP_200_OK)