from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.orders.models import Order, OrderItem
from apps.inventory.models import InventoryItem, ProductVariant, ProductVariantStatus
from apps.supplier.models import Supplier
from apps.hr.models import Employee


class OrderAPITestCase(APITestCase):
    """
    Order API 통합 테스트

    1. 주문 생성
    2. 주문 조회 / 삭제
    3. 주문 상태 변경
    4. COMPLETED 시 재고/입고 반영
    """
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="테스트공급업체",
            contact="010-1111-2222",
            manager="홍길동",
            email="supplier@example.com",
            address="서울시 성북구 안암로",
        )

        self.manager = Employee.objects.create_user(
            username="captain",
            first_name="유시진",
            password="pass",
            role="MANAGER",
            status="APPROVED",
        )

        self.product = InventoryItem.objects.create(
            product_id="P0001",
            name="테스트상품",
            category="식품",
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_code="P0001-001",
            option="기본",
            stock=100,
            price=5000,
        )

    # -------------------------------
    # 주문 생성
    # -------------------------------
    def test_order_creation(self):
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-23",
            "expected_delivery_date": "2025-07-30",
            "status": "PENDING",
            "items": [
                {
                    "variant_code": self.variant.variant_code,
                    "quantity": 10,
                    "unit_price": 5000,
                }
            ],
        }

        r = self.client.post(url, payload, format="json")

        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

    def test_order_creation_with_empty_items(self):
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-23",
            "expected_delivery_date": "2025-07-30",
            "status": "PENDING",
            "items": [],
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_creation_with_invalid_dates(self):
        url = "/api/v1/orders/"
        payload = {
            "supplier": self.supplier.id,
            "manager_name": self.manager.first_name,
            "order_date": "2025-07-30",
            "expected_delivery_date": "2025-07-20",
            "status": "PENDING",
            "items": [
                {
                    "variant_code": self.variant.variant_code,
                    "quantity": 10,
                    "unit_price": 5000,
                }
            ],
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
            "items": [
                {
                    "variant_code": "NOT_EXIST",
                    "quantity": 1,
                    "unit_price": 1000,
                }
            ],
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------
    # 주문 조회
    # -------------------------------
    def test_order_list_view(self):
        Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING",
        )

        r = self.client.get("/api/v1/orders/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data["results"]), 1)

    def test_order_detail_view(self):
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING",
        )

        r = self.client.get(f"/api/v1/orders/{order.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "PENDING")

    # -------------------------------
    # 주문 삭제
    # -------------------------------
    def test_order_deletion(self):
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING",
        )

        r = self.client.delete(f"/api/v1/orders/{order.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(id=order.id).exists())

    # -------------------------------
    # 주문 상태 변경
    # -------------------------------
    def test_order_status_change_to_completed(self):
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING",
        )
        OrderItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=5,
            unit_price=4000,
        )

        r = self.client.patch(
            f"/api/v1/orders/{order.id}/",
            {"status": "COMPLETED"},
            format="json",
        )

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, "COMPLETED")

    def test_order_completed_updates_inbound_quantity(self):
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING",
        )
        OrderItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=7,
            unit_price=4000,
        )

        r = self.client.patch(
            f"/api/v1/orders/{order.id}/",
            {"status": "COMPLETED"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        now = timezone.now()
        status_obj = ProductVariantStatus.objects.get(
            year=now.year,
            month=now.month,
            variant=self.variant,
        )
        self.assertEqual(status_obj.inbound_quantity, 7)

    def test_completed_order_cannot_be_changed(self):
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="COMPLETED",
        )

        r = self.client.patch(
            f"/api/v1/orders/{order.id}/",
            {"status": "APPROVED"},
            format="json",
        )

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("COMPLETED 상태의 주문은 변경할 수 없습니다.", r.data["error"])

    def test_invalid_order_status(self):
        order = Order.objects.create(
            supplier=self.supplier,
            manager=self.manager,
            order_date="2025-07-20",
            expected_delivery_date="2025-07-25",
            status="PENDING",
        )

        r = self.client.patch(
            f"/api/v1/orders/{order.id}/",
            {"status": "INVALID"},
            format="json",
        )

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
