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
from apps.hr.models import Employee
from apps.inventory.models import InventoryItem, ProductVariant
from apps.supplier.models import Supplier, SupplierVariant
from apps.orders.models import Order, OrderItem
from apps.hr.models import Employee
from django.utils import timezone

# 레퍼런스 참고: 한국어 더미데이터
EMPLOYEES_DATA = [
    ("admin", "MANAGER", "010-1234-5678", "active", True, True, "유시진"),
    ("manager1", "MANAGER", "010-2345-6789", "active", False, True, "넥스트"),
    ("staff1", "STAFF", "010-3456-7890", "active", False, False, "배연준"),
    ("staff2", "STAFF", "010-4567-8901", "inactive", False, False, "김정현"),
]

PRODUCTS_DATA = [
    "갤럭시 S24 Ultra", "iPhone 15 Pro", "MacBook Pro 16인치", "iPad Air",
    "Dell XPS 13", "LG 27인치 모니터", "Sony WH-1000XM5", "AirPods Pro 2세대"
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
    ProductVariant.objects.all().delete()
    InventoryItem.objects.all().delete()
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
    """상품 데이터 생성 (레퍼런스의 products 참고)"""
    print_status("상품 데이터 생성 중...", "📦")
    
    inventory_items = []
    for i, product_name in enumerate(PRODUCTS_DATA, 1):
        product_id = f'P{1000 + i}'
        
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
    """상품 옵션 생성 (description, memo 포함)"""
    print_status("상품 옵션 생성 중...", "🎨")

    product_variants = []
    for item in inventory_items:
        num_variants = random.randint(2, 4)
        selected_colors = random.sample(COLORS, min(num_variants, len(COLORS)))

        for i, color in enumerate(selected_colors, 1):
            variant_code = f"{item.product_id}-{i:02d}"

            if not ProductVariant.objects.filter(variant_code=variant_code).exists():

                variant = ProductVariant.objects.create(
                    product=item,
                    variant_code=variant_code,
                    option=color,
                    stock=random.randint(10, 100),
                    min_stock=random.randint(1, 30),
                    price=random.randint(100000, 3000000),
                    description=f"{item.name} - {color} 색상",
                    memo=random.choice(["인기 상품", "창고 보유", "입고 예정", ""]),
                    order_count = random.randint(0, 500),
                    return_count = random.randint(0, 100)
                )
                product_variants.append(variant)
            else:
                product_variants.append(ProductVariant.objects.get(variant_code=variant_code))

    print_status(f"상품 옵션 생성 완료: {len(product_variants)}개", "   ✓")
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


def display_summary():
    """생성된 데이터 요약 표시 (레퍼런스 스타일)"""
    print("\n" + "="*50)
    print("📊 생성된 더미데이터 요약:")
    print(f"   👥 직원: {Employee.objects.count()}명")
    print(f"   📦 상품: {InventoryItem.objects.count()}개")
    print(f"   🎨 상품옵션: {ProductVariant.objects.count()}개") 
    print(f"   📋 주문: {Order.objects.count()}개")
    print(f"   🏢 공급업체: {Supplier.objects.count()}개")
    
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
        
        print_status("더미데이터 생성이 완료되었습니다!", "✅")
        display_summary()
        
    except Exception as e:
        print_status(f"더미데이터 생성 중 오류가 발생했습니다: {str(e)}", "❌")
        raise

if __name__ == "__main__":
    main() 