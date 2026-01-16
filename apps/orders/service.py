# apps/orders/services/order_service.py

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import ProductVariantStatus
from apps.orders.models import Order


@transaction.atomic
def complete_order(order: Order):
    """
    Order를 COMPLETED 처리하면서
    - 해당 월 ProductVariantStatus.inbound_quantity 만 증가
    """

    if order.status == Order.STATUS_COMPLETED:
        raise ValueError("이미 COMPLETED 된 주문입니다.")

    completed_at = timezone.now()
    year = completed_at.year
    month = completed_at.month

    for item in order.items.select_related("variant", "variant__product"):
        variant = item.variant

        status_obj, created = ProductVariantStatus.objects.get_or_create(
            year=year,
            month=month,
            variant=variant,
            defaults={
                "product": variant.product,
                "inbound_quantity": item.quantity,
            }
        )

        if not created:
            status_obj.inbound_quantity += item.quantity
            status_obj.save(update_fields=["inbound_quantity"])

    order.status = Order.STATUS_COMPLETED
    order.completed_at = completed_at
    order.save(update_fields=["status", "completed_at"])
