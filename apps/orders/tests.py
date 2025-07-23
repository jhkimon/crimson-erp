import io
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.orders.models import Order, OrderItem
from apps.inventory.models import InventoryItem, ProductVariant
from apps.supplier.models import Supplier
from apps.hr.models import Employee


class OrderAPITestCase(APITestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="테스트공급업체",
            contact="010-1111-2222",
            manager="홍길동",
            email="supplier@example.com",
            address="서울시 성북구 안암로"
        )
        self.manager = Employee.objects.create_user(
            username="captain", first_name="유시진", password="pass", role="MANAGER", status="APPROVED"
        )
        self.product = InventoryItem.objects.create(product_id="P0001", name="테스트상품", category="식품")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_code="P0001-001",
            option="기본",
            stock=100,
            price=5000
        )

    def test_order_creation(self):
        """POST /api/v1/orders/ - 주문 생성"""
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-23",
            "expected_delivery_date": "2025-07-30",
            "status": "PENDING",
            "instruction_note": "빠른 배송 부탁",
            "note": "기타 요청 사항",
            "vat_included": True,
            "packaging_included": False,
            "items": [{
                "variant_code": self.variant.variant_code,
                "quantity": 10,
                "unit_price": 5000,
                "remark": "박스포장",
                "spec": "B급"
            }]
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

    def test_order_list_view(self):
        """GET /api/v1/orders/ - 주문 목록 조회"""
        # 사전 주문 생성
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING"
        )
        OrderItem.objects.create(order=order, variant=self.variant, quantity=5, unit_price=4000)

        url = "/api/v1/orders/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data["results"]), 1)

    def test_order_detail_view(self):
        """GET /api/v1/orders/{order_id}/ - 주문 조회"""
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING"
        )
        OrderItem.objects.create(order=order, variant=self.variant, quantity=5, unit_price=4000)

        url = f"/api/v1/orders/{order.id}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "PENDING")
        self.assertEqual(r.data["supplier"], self.supplier.name)

    def test_order_deletion(self):
        """DELETE /api/v1/orders/{order_id}/ - 주문 삭제"""
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING"
        )
        url = f"/api/v1/orders/{order.id}/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(id=order.id).exists())

############# 주문 상태 변경
    def test_order_status_change_to_completed(self):
        """PATCH /api/v1/orders/{order_id}/ - PENDING → COMPLETED"""
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING"
        )
        OrderItem.objects.create(order=order, variant=self.variant, quantity=5, unit_price=4000)
        prev_stock = self.variant.stock

        url = f"/api/v1/orders/{order.id}/"
        r = self.client.patch(url, {"status": "COMPLETED"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, prev_stock + 5)

    def test_order_status_change_from_completed_to_approved(self):
        """PATCH /api/v1/orders/{order_id}/ - COMPLETED → APPROVED (재고 감소)"""
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="COMPLETED"
        )
        OrderItem.objects.create(order=order, variant=self.variant, quantity=4, unit_price=4000)
        self.variant.stock = 14
        self.variant.save()

        url = f"/api/v1/orders/{order.id}/"
        r = self.client.patch(url, {"status": "APPROVED"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_order_status_change_from_completed_to_cancelled(self):
        """PATCH /api/v1/orders/{order_id}/ - COMPLETED → CANCELLED (재고 감소)"""
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="COMPLETED"
        )
        OrderItem.objects.create(order=order, variant=self.variant, quantity=4, unit_price=4000)
        self.variant.stock = 14
        self.variant.save()

        url = f"/api/v1/orders/{order.id}/"
        r = self.client.patch(url, {"status": "CANCELLED"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_order_status_change_from_completed_to_cancelled_but_insufficient_stock(self):
        """PATCH /api/v1/orders/{order_id}/ - COMPLETED → CANCELLED (재고 부족 → 400)"""
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="COMPLETED"
        )
        OrderItem.objects.create(order=order, variant=self.variant, quantity=8, unit_price=4000)
        self.variant.stock = 5  # 부족한 상태
        self.variant.save()

        url = f"/api/v1/orders/{order.id}/"
        r = self.client.patch(url, {"status": "CANCELLED"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", r.data)
        self.assertIn("현재 재고가 부족하여 상태 변경이 불가능합니다.", r.data["error"])

    def test_order_status_invalid(self):
        # PATCH /api/v1/orders/{order_id}/ - 잘못된 상태 값 처리 (유효성 검증)
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING"
        )
        url = f"/api/v1/orders/{order.id}/"
        r = self.client.patch(url, {"status": "INVALID_STATUS"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valid_choices", r.data)

############ 예외 케이스 별도 처리
    def test_order_creation_with_empty_items(self):
        """POST /api/v1/orders/ - 빈 items 리스트"""
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-23",
            "expected_delivery_date": "2025-07-30",
            "status": "PENDING",
            "items": []
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_creation_with_invalid_dates(self):
        """POST /api/v1/orders/ - 배송일이 주문일보다 빠름"""
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-30",
            "expected_delivery_date": "2025-07-20",
            "status": "PENDING",
            "items": [{
                "variant_code": self.variant.variant_code,
                "quantity": 10,
                "unit_price": 5000
            }]
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_creation_with_invalid_variant(self):
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-23",
            "expected_delivery_date": "2025-07-30",
            "status": "PENDING",
            "items": [{
                "variant_code": "NOT_EXIST_CODE",
                "quantity": 1,
                "unit_price": 1000
            }]
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)