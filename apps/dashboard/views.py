from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, F, Sum, ExpressionWrapper, IntegerField
from apps.orders.models import Order
from apps.inventory.models import ProductVariant
from apps.hr.models import VacationRequest

class DashboardSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.now().date()

        # 1. 총 매출 (완료된 주문 기준)
        total_sales = ProductVariant.objects.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("price") * (F("order_count") - F("return_count")),
                    output_field=IntegerField()
                )
            )
        )["total"] or 0

        # 2. 재고 부족 TOP 5 (stock < min_stock)
        low_stock_items = ProductVariant.objects.filter(
            stock__lt=F("min_stock")
        ).select_related("product").order_by("stock")[:5]

        top_low_stock = [
            {
                "variant_code": item.variant_code,
                "product_name": item.product.name,
                "option": item.option,
                "stock": item.stock,
                "min_stock": item.min_stock
            }
            for item in low_stock_items
        ]

        # 3. 매출 TOP 5
        top_sales_items = ProductVariant.objects.annotate(
            sales=ExpressionWrapper(
                F("price") * (F("order_count") - F("return_count")),
                output_field=IntegerField()
            )
        ).select_related("product").order_by("-sales")[:5]

        top_sales = [
            {
                "variant_code": item.variant_code,
                "option": item.option,
                "product_name": item.product.name,
                "sales": item.sales
            }
            for item in top_sales_items
        ]

        # 4. 발주 도착 임박 상품 (status=APPROVED, 가장 가까운 expected_delivery_date)
        arriving_orders = Order.objects.filter(
            status=Order.STATUS_APPROVED,
            expected_delivery_date__gte=today
        ).select_related("supplier").order_by("expected_delivery_date")[:5]

        arriving_soon = [
            {
                "order_id": order.id,
                "supplier": order.supplier.name if order.supplier else None,
                "expected_delivery_date": order.expected_delivery_date
            }
            for order in arriving_orders
        ]

        # 5. 최근 발주 현황 (order_date 순 최신 3건)
        recent_orders = Order.objects.select_related("supplier").order_by("-order_date")[:3]
        recent_order_list = [
            {
                "order_id": order.id,
                "supplier": order.supplier.name if order.supplier else None,
                "order_date": order.order_date,
                "expected_delivery_date": order.expected_delivery_date,
                "manager": order.manager.first_name if order.manager else None,
                "status": order.status,
                "product_names": list({
                    item.variant.product.name
                    for item in order.items.all()
                    if item.variant and item.variant.product
                })
            }
            for order in recent_orders
        ]

        # 6. 최근 휴가 이력 (최근 승인된 순으로 5건)
        recent_vacations = VacationRequest.objects.filter(
            status='APPROVED'
        ).select_related('employee').order_by('-created_at')[:5]

        vacation_history = [
            {
                "employee": vacation.employee.get_full_name() or vacation.employee.username,
                "leave_type": vacation.get_leave_type_display(),
                "start_date": vacation.start_date,
                "end_date": vacation.end_date,
                "created_at": vacation.created_at,
            }
            for vacation in recent_vacations
        ]
        

        return Response({
            "total_sales": total_sales,
            "top_low_stock": top_low_stock,
            "top_sales": top_sales,
            "arriving_soon_orders": arriving_soon,
            "recent_orders": recent_order_list,
            "recent_vacations": vacation_history
        })