from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from apps.orders.models import Order

class OrderAPITestCase(APITestCase):
    def setUp(self):
        # ✅ 1. 테스트 유저 생성
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # ✅ 2. JWT 토큰 발급 및 인증 헤더 설정
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)

        # ✅ 3. 테스트 주문 하나 생성
        self.order = Order.objects.create(
            variant_id="v001",
            supplier_id=1,
            quantity=5,
            status="pending"
        )

        self.list_url = "/api/v1/orders/"
        self.detail_url = f"/api/v1/orders/{self.order.id}/"
        self.status_url = f"/api/v1/orders/{self.order.id}/status/"

    def test_get_order_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("variant_id", response.data[0])

    def test_create_order(self):
        data = {
            "variant_id": "v002",
            "supplier_id": 2,
            "quantity": 10,
            "status": "confirmed"
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2)

    def test_get_order_detail(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order.id)

    def test_delete_order(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())

    def test_patch_order_status(self):
        data = {"status": "shipped", "quantity": 15}
        response = self.client.patch(self.status_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")
        self.assertEqual(self.order.quantity, 15)