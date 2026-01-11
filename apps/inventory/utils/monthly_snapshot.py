from django.db import transaction
from apps.inventory.models import ProductVariantStatus


@transaction.atomic
def rollover_variant_status(year: int, month: int):
    """
    전달 ProductVariantStatus → 다음 달로 상품 정보만 복사
    (재고 관련 필드는 전부 0으로 초기화)
    """

    # 다음 달 계산
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    prev_qs = (
        ProductVariantStatus.objects
        .select_related("product", "variant")
        .filter(year=year, month=month)
    )

    new_objects = []

    for prev in prev_qs:
        # 이미 다음 달 데이터가 있으면 스킵
        if ProductVariantStatus.objects.filter(
            year=next_year,
            month=next_month,
            variant=prev.variant,
        ).exists():
            continue

        new_objects.append(
            ProductVariantStatus(
                year=next_year,
                month=next_month,
                product=prev.product,
                variant=prev.variant,
                warehouse_stock_start=0,
                store_stock_start=0,
                inbound_quantity=0,
                store_sales=0,
                online_sales=0,
            )
        )

    ProductVariantStatus.objects.bulk_create(new_objects)

    return {
        "year": next_year,
        "month": next_month,
        "created_count": len(new_objects),
    }
