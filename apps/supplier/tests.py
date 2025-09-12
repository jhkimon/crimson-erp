from rest_framework.test import APITestCase
from rest_framework import status
from apps.inventory.models import InventoryItem, ProductVariant
from apps.supplier.models import Supplier, SupplierVariant


class SupplierAPITestCase(APITestCase):
    def setUp(self):
        self.item = InventoryItem.objects.create(
            product_id="P1000", name="테스트상품", category="식품"
        )
        self.variant1 = ProductVariant.objects.create(
            product=self.item, variant_code="P1000-A", option="기본", stock=50, price=5000
        )
        self.variant2 = ProductVariant.objects.create(
            product=self.item, variant_code="P1000-B", option="옵션B", stock=30, price=6000
        )
        self.supplier = Supplier.objects.create(
            name="테스트공급업체", contact="010-1234-5678",
            manager="유시진", email="test@supplier.com", address="서울시"
        )
        SupplierVariant.objects.create(supplier=self.supplier, variant=self.variant1)

    def test_supplier_list(self):
        """GET /api/v1/supplier/ - 공급업체 목록 조회"""
        url = "/api/v1/supplier/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data), 1)

    def test_supplier_create(self):
        """POST /api/v1/supplier/ - 공급업체 생성 (variants 포함)"""
        url = "/api/v1/supplier/"
        payload = {
            "name": "새로운공급업체",
            "contact": "010-9999-9999",
            "manager": "강하늘",
            "email": "sky@example.com",
            "address": "부산시",
            "variant_codes": [self.variant1.variant_code, self.variant2.variant_code]
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 2)
        self.assertEqual(SupplierVariant.objects.filter(supplier__name="새로운공급업체").count(), 2)

    def test_supplier_detail_view(self):
        """GET /api/v1/supplier/{id}/ - 공급업체 상세 조회"""
        url = f"/api/v1/supplier/{self.supplier.id}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["name"], self.supplier.name)
        self.assertIn("variants", r.data)

    def test_supplier_update(self):
        """PATCH /api/v1/supplier/{id}/ - 공급업체 정보 수정 + variant 재등록"""
        url = f"/api/v1/supplier/{self.supplier.id}/"
        payload = {
            "contact": "02-0000-0000",
            "variant_codes": [self.variant2.variant_code]  # 기존 variant1 제거, variant2만 등록
        }
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.contact, "02-0000-0000")
        self.assertEqual(SupplierVariant.objects.filter(supplier=self.supplier).count(), 1)
        self.assertEqual(SupplierVariant.objects.first().variant, self.variant2)

    def test_supplier_variant_patch(self):
        """PATCH /api/v1/supplier/variants/{supplier_id}/variants/{variant_code}/ - 단일 매핑 수정"""
        sv = SupplierVariant.objects.get(supplier=self.supplier, variant=self.variant1)
        url = f"/api/v1/supplier/variants/{self.supplier.id}/{self.variant1.variant_code}/"
        payload = {
            "cost_price": 4200,
            "is_primary": True
        }
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        sv.refresh_from_db()
        self.assertEqual(sv.cost_price, 4200)
        self.assertTrue(sv.is_primary)