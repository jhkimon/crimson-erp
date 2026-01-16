# Django
from datetime import date

from django.db import transaction
from django.db.models import Sum, Q

# DRF
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Models
from apps.orders.models import Order, OrderItem
from apps.inventory.models import (
    ProductVariant,
    ProductVariantStatus,
)


class SyncInboundFromOrdersView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="발주 기준 재고 입고량 자동 반영",
        operation_description=(
            "해당 월 발주 데이터를 기준으로\n"
            "ProductVariantStatus.inbound_quantity를 자동 갱신합니다.\n\n"
            "기준:\n"
            "- completed_at 있으면 completed_at\n"
            "- 없으면 expected_delivery_date\n\n"
            "동작:\n"
            "- variant별 발주 수량 합계\n"
            "- inbound_quantity 덮어쓰기"
        ),
        manual_parameters=[
            openapi.Parameter(
                "year",
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
            openapi.Parameter(
                "month",
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="동기화 결과",
                examples={
                    "application/json": {
                        "message": "발주 데이터 반영 완료",
                        "updated": 12
                    }
                }
            )
        },
        tags=["inventory"],
    )
    def post(self, request, year: int, month: int):

        if not (1 <= month <= 12):
            return Response(
                {"detail": "month는 1~12"},
                status=400
            )

        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        # 1. 해당 월 주문 필터
        orders = Order.objects.filter(
            Q(
                completed_at__isnull=False,
                completed_at__gte=start,
                completed_at__lt=end,
            )
            |
            Q(
                completed_at__isnull=True,
                expected_delivery_date__gte=start,
                expected_delivery_date__lt=end,
            )
        )

        # 2. variant별 수량 집계
        summary = (
            OrderItem.objects
            .filter(order__in=orders)
            .values("variant")
            .annotate(total_qty=Sum("quantity"))
        )

        updated = 0

        with transaction.atomic():

            for row in summary:
                variant_id = row["variant"]
                qty = row["total_qty"]

                variant = ProductVariant.objects.get(id=variant_id)

                status_obj, _ = ProductVariantStatus.objects.get_or_create(
                    year=year,
                    month=month,
                    variant=variant,
                    defaults={
                        "product": variant.product,
                        "inbound_quantity": qty,
                    }
                )

                # 이미 있으면 덮어쓰기
                status_obj.inbound_quantity = qty
                status_obj.save(update_fields=["inbound_quantity"])

                updated += 1

        return Response(
            {
                "message": "발주 데이터 반영 완료",
                "updated": updated
            }
        )
