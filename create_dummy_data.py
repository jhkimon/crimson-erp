#!/usr/bin/env python3
"""
CrimsonERP 프로젝트용 더미데이터 생성 스크립트
프론트엔드 개발자가 복잡한 DB 설정 없이 바로 API 테스트할 수 있도록 함

실행: python create_dummy_data.py
옵션: --reset (기존 데이터 삭제 후 새로 생성), --force (기존 데이터 있어도 추가)
"""

import os
import sys
import django
import random
import argparse
from datetime import datetime, timedelta

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crimsonerp.settings')
django.setup()

# Django 모델 import (django.setup() 이후에 해야 함)
from apps.hr.models import Employee, VacationRequest
from apps.inventory.models import InventoryItem, ProductVariant, InventoryAdjustment
from apps.supplier.models import Supplier, SupplierVariant
from apps.orders.models import Order, OrderItem
from apps.hr.models import Employee
from django.utils import timezone

# 레퍼런스 참고: 한국어 더미데이터
EMPLOYEES_DATA = [
    ("admin", "MANAGER", "010-1234-5678", "APPROVED", True, True, "유시진"),
    ("manager1", "MANAGER", "010-2345-6789", "APPROVED", False, True, "넥스트"),
    ("staff1", "STAFF", "010-3456-7890", "APPROVED", False, False, "배연준"),
    ("staff2", "STAFF", "010-4567-8901", "DENIED", False, False, "김정현"),
]

PRODUCTS_DATA = [
    "2025년 탁상용 달력",
    "2025년 벽걸이 달력",
    "미니 에코백 (코리아)",
    "L 홀더 (파일)",
    "수저 세트",
    "방패 필통",
    "고려대 피규어 키링",
    "세도나 볼펜",
    "슬립 텀블러",
    "호이 야구잠바 인형",
    "호이 키링 인형"
]

VARIANT_DATA = [
    ("P00000OD", None, "2025년 탁상용 달력", "", 9000, 0, 65, 0),
    ("P0000BDB", None, "2025년 탁상용 달력", "", 9000, 0, 64, 0),
    ("P00000NB", None, "미니 에코백 (코리아)", "", 6000, 0, 50, 0),
    ("P00000XN", "P00000XN000A", "L 홀더 (파일)", "디자인 : 초충도첩 식물", 500, 74, 35, 0),
    ("P0000BBO", None, "수저 세트", "", 12000, 0, 22, 1),
    ("P00000YC", "P00000YC000A", "방패 필통", "색상 : 크림슨", 5000, 100, 19, 0),
    ("P00000ZQ", "P00000ZQ000A", "고려대 피규어 키링", "디자인 : 남학생", 8800, 90, 16, 0),
    ("P00000PR", "P00000PR000A", "슬립 텀블러", "색상 : 아이보리", 19000, 40, 15, 0),
    ("P00000OY", None, "호이 야구잠바 인형", "", 27000, 0, 15, 0),
    ("P00000OW", "P00000OW000B", "호이 키링 인형", "색상 : 크림슨", 12000, 0, 14, 0),
    ("P00000YC", "P00000YC000C", "방패 필통", "색상 : 블랙", 5000, 0, 13, 0),
]


SUPPLIERS_DATA = [
    ("대한유통", "010-6675-7797", "박한솔", "hspark_factcorp@kakao.com", "서울특별시 성북구 안암로145"),
    ("삼성상사", "010-1234-5678", "김진수", "samsung@corp.com", "서울특별시 강남구 테헤란로 311"),
    ("LG트레이딩", "010-8888-9999", "이현주", "lgtrade@lg.com", "서울특별시 마포구 월드컵북로 396"),
    ("넥스트물류", "010-2222-3333", "정민호", "nextlogi@next.com", "경기도 성남시 판교로 242"),
]

COLORS = ["블랙", "화이트", "실버", "골드", "블루", "레드", "그린", "퍼플"]
ORDER_STATUSES = ["PENDING", "APPROVED", "CANCELLED"]


def print_status(message, emoji="🔹"):
    """상태 메시지 출력"""
    print(f"{emoji} {message}")


def has_existing_data():
    """기존 데이터가 있는지 확인"""
    return (
        Employee.objects.exists() or 
        InventoryItem.objects.exists() or 
        Order.objects.exists()
    )


def reset_data():
    """기존 데이터 삭제 (FK 관계 순서 고려)"""
    print_status("기존 데이터를 삭제합니다...", "🔄")
    Order.objects.all().delete()
    SupplierVariant.objects.all().delete()
    ProductVariant.objects.all().delete()
    InventoryItem.objects.all().delete()
    Supplier.objects.all().delete()
    Employee.objects.all().delete()
    print_status("기존 데이터 삭제 완료", "✓")


def create_employees():
    """직원 데이터 생성 (레퍼런스 참고)"""
    print_status("직원 데이터 생성 중...", "👥")
    
    employees = []
    for username, role, contact, status, is_superuser, is_staff, real_name in EMPLOYEES_DATA:
        
        if not Employee.objects.filter(username=username).exists():
            employee = Employee.objects.create_user(
                username=username,
                email=f'{username}@crimsonerp.com',
                password='crimson123',  # 테스트용 통일 비밀번호
                first_name=real_name,
                last_name='',
                role=role,
                contact=contact,
                status=status,
                is_superuser=is_superuser,
                is_staff=is_staff,
            )
            employees.append(employee)
            print_status(f"직원 생성: {real_name} ({username}, {role})", "   ✓")
        else:
            employees.append(Employee.objects.get(username=username))
    
    return employees


def create_inventory_items():
    """VARIANT_DATA 기반으로 상품 생성"""
    print_status("상품 데이터 생성 중...", "📦")

    seen = set()
    inventory_items = []

    for product_id, _, product_name, *_ in VARIANT_DATA:
        if product_id in seen:
            continue
        seen.add(product_id)

        if not InventoryItem.objects.filter(product_id=product_id).exists():
            item = InventoryItem.objects.create(
                product_id=product_id,
                name=product_name
            )
            inventory_items.append(item)
            print_status(f"상품 생성: {product_name} ({product_id})", "   ✓")
        else:
            inventory_items.append(InventoryItem.objects.get(product_id=product_id))

    return inventory_items

def create_product_variants(inventory_items):
    """실제 상품 및 옵션 기반으로 ProductVariant 생성"""
    print_status("상품 옵션 생성 중 (실제값 기반)...", "🎯")
    product_variants = []

    # InventoryItem dict for fast lookup
    product_dict = {item.product_id: item for item in inventory_items}

    for product_id, variant_code, name, option, price, stock, order_count, return_count in VARIANT_DATA:
        if product_id not in product_dict:
            continue  # 해당 상품이 inventory에 없으면 생략

        product = product_dict[product_id]
        final_variant_code = variant_code or f"{product_id}000A"

        if not ProductVariant.objects.filter(variant_code=final_variant_code).exists():
            variant = ProductVariant.objects.create(
                product=product,
                variant_code=final_variant_code,
                option=option or "기본",
                stock=stock,
                min_stock=random.randint(1, 10),
                price=price,
                description=f"{name} {option}".strip(),
                memo=random.choice(["", "인기 상품", "한정 재고"]),
                order_count=order_count,
                return_count=return_count,
                is_active=True,
            )
            product_variants.append(variant)
        else:
            variant = ProductVariant.objects.get(variant_code=final_variant_code)
            product_variants.append(variant)

    print_status(f"실제 상품 옵션 생성 완료: {len(product_variants)}개", "   ✓")
    return product_variants

def create_suppliers(product_variants):
    """공급업체 및 SupplierVariant 연결"""
    print_status("공급업체 데이터 생성 중...", "🏢")

    # 1. 공급업체 생성
    suppliers = []
    for name, contact, manager, email, address in SUPPLIERS_DATA:
        supplier, created = Supplier.objects.get_or_create(
            name=name,
            defaults={
                "contact": contact,
                "manager": manager,
                "email": email,
                "address": address,
            }
        )
        suppliers.append(supplier)
        print_status(f"공급업체 생성: {name}", "   ✓" if created else "   •")

    # 2. 모든 variant를 최소 하나의 공급업체에 매핑 (순환 방식)
    supplier_count = len(suppliers)
    for i, variant in enumerate(product_variants):
        primary_supplier = suppliers[i % supplier_count]
        _link_supplier_variant(primary_supplier, variant, is_primary=True)

    # 3. 일부 variant는 추가 supplier 1~2개와 연결 (is_primary=False)
    extra_variants = random.sample(product_variants, k=int(len(product_variants) * 0.4))  # 약 40%만 추가 연결
    for variant in extra_variants:
        available_suppliers = [s for s in suppliers if not SupplierVariant.objects.filter(supplier=s, variant=variant).exists()]
        extra_suppliers = random.sample(available_suppliers, k=min(len(available_suppliers), random.randint(1, 2)))
        for supplier in extra_suppliers:
            _link_supplier_variant(supplier, variant, is_primary=False)

    print_status(f"총 {len(suppliers)}개의 공급업체 등록 및 매핑 완료", "✓")
    return suppliers


def _link_supplier_variant(supplier, variant, is_primary=False):
    """SupplierVariant 안전 연결 및 누락 필드 보완"""
    cost_price = int(variant.price * random.uniform(0.6, 0.8))
    lead_time_days = random.randint(2, 10)

    sv, created = SupplierVariant.objects.get_or_create(
        supplier=supplier,
        variant=variant,
        defaults={
            "cost_price": cost_price,
            "lead_time_days": lead_time_days,
            "is_primary": is_primary
        }
    )

    if not created:
        updated = False
        if sv.cost_price is None:
            sv.cost_price = cost_price
            updated = True
        if sv.lead_time_days is None:
            sv.lead_time_days = lead_time_days
            updated = True
        if sv.is_primary is None:
            sv.is_primary = is_primary
            updated = True
        if updated:
            sv.save()

def create_orders(product_variants):
    print_status("주문 데이터 생성 중...", "📋")

    if not product_variants:
        print_status("상품 옵션이 없어 주문을 생성할 수 없습니다.", "⚠️")
        return []

    manager_pool = list(Employee.objects.all())
    print("manager_pool:", manager_pool)
    if not manager_pool:
        print_status("매니저 계정이 없어 주문에 할당할 수 없습니다.", "⚠️")
        return []

    orders = []

    for _ in range(20):
        # ✅ supplier와 연결된 variant만 필터
        eligible_variants = [
            v for v in product_variants
            if SupplierVariant.objects.filter(variant=v).exists()
        ]
        if len(eligible_variants) < 1:
            continue

        num_items = random.randint(1, 4)
        selected_variants = random.sample(eligible_variants, k=min(num_items, len(eligible_variants)))

        # ✅ 각 variant가 연결된 supplier 중에서 가장 많이 겹치는 공급업체 선택
        supplier_counts = {}
        for variant in selected_variants:
            for sv in SupplierVariant.objects.filter(variant=variant):
                supplier_counts[sv.supplier] = supplier_counts.get(sv.supplier, 0) + 1

        if not supplier_counts:
            continue

        # 가장 많은 variant와 연결된 공급업체 선택
        supplier = max(supplier_counts.items(), key=lambda x: x[1])[0]
        manager = random.choice(manager_pool)

        order = Order.objects.create(
            supplier=supplier,
            manager=manager,
            status=random.choice(ORDER_STATUSES),
            order_date=timezone.now() - timedelta(days=random.randint(0, 30)),
            expected_delivery_date=timezone.now() + timedelta(days=random.randint(2, 14)),
            instruction_note=random.choice(["포장 필수", "입고 후 확인 전화 요망", "문 앞 비대면 수령", ""]),
            note=random.choice(["긴급 요청", "기본 주문", ""])
        )

        for variant in selected_variants:
            try:
                supplier_variant = SupplierVariant.objects.get(variant=variant, supplier=supplier)
            except SupplierVariant.DoesNotExist:
                continue

            OrderItem.objects.create(
                order=order,
                variant=variant,
                item_name=variant.product.name,
                spec=variant.option,
                quantity=random.randint(1, 50),
                unit_price=supplier_variant.cost_price,
                remark=random.choice(["단가 협의됨", ""])
            )

        orders.append(order)

    print_status(f"주문 데이터 생성 완료: {len(orders)}개", "✓")
    return orders

def create_vacation_requests(employees):
    """직원별 휴가 요청 더미 데이터 생성"""
    print_status("휴가 요청 데이터 생성 중...", "🌴")

    LEAVE_TYPES = ['VACATION', 'HALF_DAY_AM', 'HALF_DAY_PM', 'SICK', 'OTHER']
    STATUSES = ['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED']

    count = 0
    for employee in employees:
        n_requests = random.randint(2, 4)
        for _ in range(n_requests):
            leave_type = random.choice(LEAVE_TYPES)
            status = random.choice(STATUSES)
            start_date = timezone.now().date() + timedelta(days=random.randint(-30, 30))
            if leave_type in ['HALF_DAY_AM', 'HALF_DAY_PM']:
                end_date = start_date
            else:
                end_date = start_date + timedelta(days=random.randint(0, 3))

            VacationRequest.objects.create(
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=random.choice(["개인 사정", "가족 행사", "병원 진료", "휴식 필요", "기타"]),
                status=status,
                reviewed_at=timezone.now() if status != 'PENDING' else None
            )
            count += 1
    print_status(f"총 {count}개의 휴가 요청 생성 완료", "   ✓")

def create_inventory_adjustments(product_variants):
    """ProductVariant 기반 재고 조정 더미 생성"""
    print_status("재고 조정 데이터 생성 중...", "🔧")

    if not product_variants:
        print_status("상품 옵션이 없어 재고 조정을 생성할 수 없습니다.", "⚠️")
        return []

    reasons = ["입고 오류 수정", "파손/불량", "기초 재고 등록", "정기 재고조사", "기타"]
    adjustments = []

    for variant in random.sample(product_variants, k=min(5, len(product_variants))):
        delta = random.randint(-5, 10)
        reason = random.choice(reasons)
        created_by = random.choice(Employee.objects.filter(is_staff=True)).username  # 사용자명

        # 재고 업데이트
        variant.stock = max(0, variant.stock + delta)
        variant.save()

        adjustment = InventoryAdjustment.objects.create(
            variant=variant,
            delta=delta,
            reason=reason,
            created_by=created_by,
        )

        adjustments.append(adjustment)

    print_status(f"총 {len(adjustments)}개의 재고 조정 생성 완료", "   ✓")
    return adjustments

def display_summary():
    """생성된 데이터 요약 표시 (레퍼런스 스타일)"""
    print("\n" + "="*50)
    print("📊 생성된 더미데이터 요약:")
    print(f"   👥 직원: {Employee.objects.count()}명")
    print(f"   📦 상품: {InventoryItem.objects.count()}개")
    print(f"   🎨 상품옵션: {ProductVariant.objects.count()}개") 
    print(f"   📋 주문: {Order.objects.count()}개")
    print(f"   🏢 공급업체: {Supplier.objects.count()}개")
    print(f"   🌴 휴가 요청: {VacationRequest.objects.count()}개")
    print(f"   🔧 재고 조정 기록: {InventoryAdjustment.objects.count()}개")
    
    print("\n🔑 테스트 계정 정보:")
    
    print("\n🔑 테스트 계정 정보:")
    print("   - admin / crimson123 (관리자)")
    print("   - manager1 / crimson123 (매니저)")
    print("   - staff1 / crimson123 (스태프)")
    print("   - staff2 / crimson123 (스태프, 비활성)")
    
    print("\n🚀 이제 다음 명령어로 서버를 시작할 수 있습니다:")
    print("   python manage.py runserver")
    print("\n📖 API 문서:")
    print("   http://localhost:8000/swagger/")
    print("="*50)



def main():
    parser = argparse.ArgumentParser(description='CrimsonERP 더미데이터 생성')
    parser.add_argument('--reset', action='store_true', help='기존 데이터를 모두 삭제하고 새로 생성')
    parser.add_argument('--force', action='store_true', help='기존 데이터가 있어도 강제로 추가')
    
    args = parser.parse_args()
    
    print("🎯 CrimsonERP 더미데이터 생성을 시작합니다...")
    
    # Reset 옵션이 있으면 기존 데이터 삭제
    if args.reset:
        reset_data()
    
    # 이미 데이터가 있는지 체크
    if not args.force and not args.reset and has_existing_data():
        print("⚠️  이미 데이터가 존재합니다. --force 또는 --reset 옵션을 사용해주세요.")
        print("   예시: python create_dummy_data.py --force")
        return
    
    try:
        # 레퍼런스 참고: 순서대로 생성 (FK 관계 고려)
        employees = create_employees()
        inventory_items = create_inventory_items()
        product_variants = create_product_variants(inventory_items)
        suppliers = create_suppliers(product_variants)
        orders = create_orders(product_variants)
        vacation_requests = create_vacation_requests(employees)
        inventory_adjustments = create_inventory_adjustments(product_variants)
        
        print_status("더미데이터 생성이 완료되었습니다!", "✅")
        display_summary()
        
    except Exception as e:
        print_status(f"더미데이터 생성 중 오류가 발생했습니다: {str(e)}", "❌")
        raise

if __name__ == "__main__":
    main() 