import io
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.inventory.models import (
    InventoryItem,
    ProductVariant,
    InventoryAdjustment
)


class InventoryQuickViewTest(APITestCase):

    def setUp(self):
        InventoryItem.objects.create(product_id="P00001", name="방패 필통")
        InventoryItem.objects.create(product_id="P00002", name="삼방패 티셔츠")

    def test_product_option_list(self):
        url = reverse("inventory_options")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("product_id", response.data[0])
        self.assertIn("name", response.data[0])

class ProductVariantCreateTest(APITestCase):

    def test_create_variant(self):
        url = reverse("variant")
        payload = {
            "product_id": "P00010",
            "name": "방패 필통",
            "category": "문구",
            "option": "색상: 크림슨",
            "stock": 100,
            "price": 5900,
            "min_stock": 5,
            "channels": ["online", "offline"]
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        variant = ProductVariant.objects.first()
        self.assertEqual(variant.product.product_id, "P00010")
        self.assertEqual(variant.stock, 100)
        self.assertIn("variant_code", response.data)


class ProductVariantListTest(APITestCase):

    def setUp(self):
        product = InventoryItem.objects.create(product_id="P00020", name="방패 필통")
        ProductVariant.objects.create(
            product=product,
            variant_code="P00020000A",
            option="크림슨",
            stock=50,
            price=5000
        )

    def test_variant_list(self):
        url = reverse("variant")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)


class ProductVariantDetailTest(APITestCase):

    def setUp(self):
        self.product = InventoryItem.objects.create(
            product_id="P00030", name="삼방패 티셔츠"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_code="P00030000A",
            option="화이트 M",
            stock=30,
            price=12000
        )

    def test_get_variant_detail(self):
        url = reverse("variant-detail", args=[self.variant.variant_code])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["variant_code"], self.variant.variant_code)

    def test_patch_variant(self):
        url = reverse("variant-detail", args=[self.variant.variant_code])
        payload = {"price": 11000}

        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.price, 11000)

    def test_delete_variant(self):
        url = reverse("variant-detail", args=[self.variant.variant_code])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(ProductVariant.objects.count(), 0)


class StockAdjustmentTest(APITestCase):

    def setUp(self):
        product = InventoryItem.objects.create(
            product_id="P00040", name="방패 필통"
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            variant_code="P00040000A",
            option="블랙",
            stock=100
        )

    def test_stock_update_creates_adjustment(self):
        url = reverse("stock-update", args=[self.variant.variant_code])
        payload = {
            "actual_stock": 90,
            "reason": "분기 실사",
            "updated_by": "관리자A"
        }

        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 90)
        self.assertEqual(self.variant.adjustment, 0)

        adjustment = InventoryAdjustment.objects.first()
        self.assertEqual(adjustment.delta, -10)
        self.assertEqual(adjustment.created_by, "관리자A")


class InventoryAdjustmentListTest(APITestCase):

    def setUp(self):
        product = InventoryItem.objects.create(
            product_id="P00050", name="삼방패 티셔츠"
        )
        variant = ProductVariant.objects.create(
            product=product,
            variant_code="P00050000A",
            option="L",
            stock=50
        )
        InventoryAdjustment.objects.create(
            variant=variant,
            delta=-5,
            reason="파손",
            created_by="관리자B"
        )

    def test_adjustment_list(self):
        url = reverse("inventory-adjustments")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn("variant_code", response.data["results"][0])
