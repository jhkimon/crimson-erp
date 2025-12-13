#!/usr/bin/env python3
import os
import django
import random
import argparse
from datetime import timedelta, date
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crimsonerp.settings")
django.setup()

# =====================
# 모델 import
# =====================
from apps.hr.models import Employee, VacationRequest
from apps.inventory.models import (
    InventoryItem,
    ProductVariant,
    ProductVariantStatus,
    InventoryAdjustment,
)
from apps.supplier.models import Supplier
from apps.orders.models import Order, OrderItem

# =====================
# 더미 데이터 정의
# =====================
EMPLOYEES = [
    {
        "username": "admin",
        "name": "유시진",
        "role": "MANAGER",
        "is_superuser": True,
        "is_staff": True,
        "allowed_tabs": ["SUPPLIER", "ORDER", "INVENTORY", "HR"],
        "gender": "MALE",
    },
    {
        "username": "manager1",
        "name": "넥스트",
        "role": "MANAGER",
        "is_superuser": False,
        "is_staff": True,
        "allowed_tabs": ["ORDER", "INVENTORY"],
        "gender": "MALE",
    },
    {
        "username": "staff1",
        "name": "배연준",
        "role": "STAFF",
        "is_superuser": False,
        "is_staff": False,
        "allowed_tabs": ["INVENTORY"],
        "gender": "MALE",
    },
    {
        "username": "staff2",
        "name": "김정현",
        "role": "STAFF",
        "is_superuser": False,
        "is_staff": False,
        "allowed_tabs": ["INVENTORY"],
        "gender": "FEMALE",
    },
]

PRODUCTS = [
    ("P00001", "2025년 탁상용 달력"),
    ("P00002", "미니 에코백"),
    ("P00003", "수저 세트"),
    ("P00004", "텀블러"),
]

VARIANTS = [
    ("P00001", "P00001-A", "기본", 9000, 50),
    ("P00002", "P00002-A", "오프화이트", 6000, 30),
    ("P00003", "P00003-A", "1세트", 12000, 20),
    ("P00004", "P00004-A", "아이보리", 19000, 15),
]

SUPPLIERS = [
    ("대한유통", "010-1111-2222", "박한솔"),
    ("삼성상사", "010-3333-4444", "김진수"),
]

ORDER_STATUSES = [
    Order.STATUS_PENDING,
    Order.STATUS_APPROVED,
    Order.STATUS_COMPLETED,
]

# =====================
# 유틸
# =====================
def log(msg, emoji="•"):
    print(f"{emoji} {msg}")

# =====================
# 리셋
# =====================
def reset_data():
    log("기존 데이터 삭제 중...", "🔄")
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    InventoryAdjustment.objects.all().delete()
    ProductVariantStatus.objects.all().delete()
    ProductVariant.objects.all().delete()
    InventoryItem.objects.all().delete()
    Supplier.objects.all().delete()
    VacationRequest.objects.all().delete()
    Employee.objects.all().delete()
    log("기존 데이터 삭제 완료", "✓")

# =====================
# 직원
# =====================
def create_employees():
    log("직원 생성", "👥")
    employees = []

    for e in EMPLOYEES:
        user = Employee.objects.create_user(
            username=e["username"],
            password="crimson123",
            first_name=e["name"],
            role=e["role"],
            status="APPROVED",
            is_superuser=e["is_superuser"],
            is_staff=e["is_staff"],
            allowed_tabs=e["allowed_tabs"],
            gender=e["gender"],
            hire_date=date.today() - timedelta(days=random.randint(30, 700)),
        )
        employees.append(user)

    return employees

# =====================
# 휴가
# =====================
def create_vacations(employees):
    log("휴가 요청 생성", "🌴")

    for emp in employees:
        for _ in range(random.randint(1, 3)):
            start = date.today() - timedelta(days=random.randint(1, 60))
            end = start + timedelta(days=random.randint(0, 2))

            VacationRequest.objects.create(
                employee=emp,
                leave_type=random.choice([
                    "VACATION",
                    "HALF_DAY_AM",
                    "HALF_DAY_PM",
                    "SICK",
                ]),
                start_date=start,
                end_date=end,
                status=random.choice([
                    "APPROVED",
                    "PENDING",
                    "REJECTED",
                ]),
                reason="개발용 더미 휴가",
                reviewed_at=timezone.now(),
            )

# =====================
# 상품
# =====================
def create_products():
    log("상품 생성 (대분류/중분류/카테고리 포함)", "📦")
    items = []

    for pid, name in PRODUCTS:
        item = InventoryItem.objects.create(
            product_id=pid,

            # 엑셀 기준 필드
            big_category="굿즈",
            middle_category="문구" if "달력" in name or "홀더" in name else "생활용품",
            category="일반",

            name=name,                       # 오프라인 품목명
            online_name=f"[온라인] {name}",  # 온라인 품목명
            description=f"{name} 더미 상품 설명입니다.",
        )
        items.append(item)

    return items

def create_variants(items):
    log("상품 옵션 생성", "🎯")
    variants = []
    item_map = {i.product_id: i for i in items}

    for pid, code, option, price, stock in VARIANTS:
        variant = ProductVariant.objects.create(
            product=item_map[pid],
            variant_code=code,
            option=option,
            price=price,
            cost_price=int(price * 0.6),
            stock=stock,
            min_stock=5,
            memo="더미 데이터",
        )
        variants.append(variant)

    return variants

# =====================
# 공급업체
# =====================
def create_suppliers():
    log("공급업체 생성", "🏢")
    suppliers = []

    for name, contact, manager in SUPPLIERS:
        suppliers.append(
            Supplier.objects.create(
                name=name,
                contact=contact,
                manager=manager,
                address="서울시 성북구",
            )
        )
    return suppliers

# =====================
# 주문
# =====================
def create_orders(variants, suppliers, employees):
    log("주문 생성", "📋")

    for _ in range(10):
        supplier = random.choice(suppliers)
        manager = random.choice(employees)

        order = Order.objects.create(
            supplier=supplier,
            manager=manager,
            order_date=date.today() - timedelta(days=random.randint(1, 30)),
            expected_delivery_date=date.today() + timedelta(days=7),
            status=random.choice(ORDER_STATUSES),
            note="더미 주문",
        )

        for v in random.sample(variants, k=random.randint(1, 3)):
            OrderItem.objects.create(
                order=order,
                variant=v,
                item_name=v.product.name,
                spec=v.option,
                quantity=random.randint(1, 20),
                unit_price=v.price,
            )

# =====================
# 재고 조정
# =====================
def create_inventory_adjustments(variants, employees):
    log("재고 조정 생성", "🔧")

    for v in random.sample(variants, k=min(3, len(variants))):
        delta = random.randint(-5, 10)

        InventoryAdjustment.objects.create(
            variant=v,
            delta=delta,
            reason="개발용 재고 보정",
            created_by=random.choice(employees).username,
        )

        v.stock = max(0, v.stock + delta)
        v.save()

# =====================
# 상품 월별 상태
# =====================

def create_product_variant_statuses(variants):
    print("📊 상품 월별 상태(ProductVariantStatus) 생성 중...")

    today = timezone.now().date()
    year = today.year
    month = today.month

    for variant in variants:
        ProductVariantStatus.objects.create(
            year=year,
            month=month,
            product=variant.product,
            variant=variant,
            warehouse_stock_start=random.randint(0, 50),
            store_stock_start=random.randint(0, 30),
            inbound_quantity=random.randint(0, 40),
            store_sales=random.randint(0, 20),
            online_sales=random.randint(0, 15),
            stock_adjustment=variant.adjustment,
            stock_adjustment_reason="더미 생성",
        )

    print(f"   ✓ {len(variants)}개의 ProductVariantStatus 생성 완료")

# =====================
# 메인
# =====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    print("🎯 CrimsonERP 더미데이터 생성 시작")

    if args.reset:
        reset_data()

    employees = create_employees()
    create_vacations(employees)
    items = create_products()
    variants = create_variants(items)
    create_product_variant_statuses(variants)
    suppliers = create_suppliers()
    create_orders(variants, suppliers, employees)
    create_inventory_adjustments(variants, employees)

    print("\n✅ 더미데이터 생성 완료")

if __name__ == "__main__":
    main()
