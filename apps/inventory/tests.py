from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from apps.inventory.models import InventoryItem, ProductVariant

class InventoryAPITestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="testpass123"
        )

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.item = InventoryItem.objects.create(
            product_id="P001", name="Test Item"
        )
        self.variant = ProductVariant.objects.create(
            product=self.item,
            variant_code="V001",
            option="Red",
            stock=10,
            price=1000
        )

        # ✅ URL 경로들
        self.list_url = "/api/v1/inventory/items/"
        self.detail_url = f"/api/v1/inventory/items/{self.item.id}/"
        self.variant_url = f"/api/v1/inventory/items/{self.item.id}/variants/"
        self.variant_detail_url = f"/api/v1/inventory/items/{self.item.id}/variants/{self.variant.id}/"

    def test_get_inventory_list(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_create_inventory_item(self):
        data = {"product_id": "P002", "name": "New Item"}
        res = self.client.post(self.list_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_get_inventory_item_detail(self):
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_inventory_item(self):
        data = {"product_id": "P001", "name": "Updated Name"}
        res = self.client.put(self.detail_url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_inventory_item(self):
        res = self.client.delete(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_product_variant(self):
        data = {
            "variant_code": "V002",
            "option": "Blue",
            "stock": 20,
            "price": 3000
        }
        res = self.client.post(self.variant_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_product_variant(self):
        data = {
            "variant_code": "V001",
            "option": "Black",
            "stock": 15,
            "price": 2500
        }
        res = self.client.put(self.variant_detail_url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_product_variant(self):
        res = self.client.delete(self.variant_detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)