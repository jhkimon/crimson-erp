from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order


@transaction.atomic
def complete_order(order: Order):
    """
    Order를 COMPLETED 처리
    - 통계(ProductVariantStatus)는 건드리지 않음
    - Sync API에서 일괄 계산
    """

    if order.status == Order.STATUS_COMPLETED:
        raise ValueError("이미 COMPLETED 된 주문입니다.")

    completed_at = timezone.now()

    order.status = Order.STATUS_COMPLETED
    order.completed_at = completed_at
    order.save(update_fields=["status", "completed_at"])