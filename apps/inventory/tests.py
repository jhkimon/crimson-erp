import io
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.inventory.models import InventoryItem, ProductVariant, InventoryAdjustment
from apps.hr.models import Employee
from .serializers import InventoryAdjustmentSerializer
from django.core.files.uploadedfile import SimpleUploadedFile
import pandas as pd


class InventoryAPITestCase(APITestCase):
    def setUp(self):
        # 직원(조정 생성자) 샘플
        self.user = Employee.objects.create_user(
            username="tester", email="tester@example.com", password="pass",
            first_name="테스터", role="STAFF", status="APPROVED"
        )

        # 상품 및 Variant 샘플
        self.item = InventoryItem.objects.create(
            product_id="PTEST01", name="테스트 상품", category="테스트카테고리"
        )
        self.variant = ProductVariant.objects.create(
            product=self.item,
            variant_code="PTEST01-001",
            option="기본",
            stock=10,
            min_stock=5,
            price=1000,
            description="테스트용",
            memo="",
            cost_price=800,
            order_count=2,
            return_count=0
        )

        # 기존 재고 조정 이력 하나 생성
        self.adjustment = InventoryAdjustment.objects.create(
            variant=self.variant,
            delta=+3,
            reason="초기 적재",
            created_by=self.user.username
        )

    def test_product_option_list(self):
        """GET /api/v1/inventory/ → product_id/name 드롭다운 조회"""
        url = "/api/v1/inventory/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # 최소 하나의 항목이 product_id/name 포함
        self.assertIn("product_id", r.data[0])
        self.assertIn("name", r.data[0])

    def test_inventory_item_detail(self):
        """GET /api/v1/inventory/{product_id}/ → variants 포함 상세 조회"""
        url = f"/api/v1/inventory/{self.item.product_id}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["product_id"], self.item.product_id)
        self.assertIsInstance(r.data["variants"], list)
        # variants[0] 에 variant_code 가 맞는지
        self.assertEqual(r.data["variants"][0]["variant_code"], self.variant.variant_code)

    def test_stock_update_creates_adjustment(self):
        """PUT /api/v1/inventory/variants/stock/{variant_code}/ → 재고조정 & 이력 생성"""
        url = f"/api/v1/inventory/variants/stock/{self.variant.variant_code}/"
        payload = {"actual_stock": 20, "reason": "실사", "updated_by": self.user.username}
        r = self.client.put(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # stock 이 20 으로 바뀌었는지
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 20)
        # adjustment 레코드가 하나 더 생성됐는지
        self.assertEqual(InventoryAdjustment.objects.filter(variant=self.variant).count(), 2)
        last = InventoryAdjustment.objects.filter(variant=self.variant).order_by("created_at").last()
        self.assertEqual(last.delta, 20 - 10)

        # 예외 1. actual_stock 누락
        payload_missing_field = {"reason": "누락 테스트", "updated_by": self.user.username}
        r1 = self.client.put(url, payload_missing_field, format="json")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.data["error"], "actual_stock is required")

        # 예외 2. 존재하지 않는 코드
        url_invalid = "/api/v1/inventory/variants/stock/NON_EXISTENT_CODE/"
        payload = {"actual_stock": 10, "reason": "없는 코드", "updated_by": self.user.username}
        r2 = self.client.put(url_invalid, payload, format="json")
        self.assertEqual(r2.status_code, 404)

        

    def test_inventory_adjustment_list_and_filter(self):
        """GET /api/v1/inventory/adjustments/ → 전체/필터 조회"""
        url = "/api/v1/inventory/adjustments/"
        # 1) 전체 조회
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data["results"]), 1)

        # 2) variant_code 로 필터
        r2 = self.client.get(url + f"?variant_code={self.variant.variant_code}")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        for adj in r2.data["results"]:
            self.assertEqual(adj["variant_code"], self.variant.variant_code)

        url_invalid = "/api/v1/inventory/NON_EXISTENT/"
        r = self.client.get(url_invalid)
        self.assertEqual(r.status_code, 404)

    def test_adjustment_serializer_fields(self):
        """InventoryAdjustmentSerializer 가 올바른 필드를 뱉는지 검증"""
        serializer = InventoryAdjustmentSerializer(self.adjustment)
        data = serializer.data
        self.assertEqual(data["variant_code"], self.variant.variant_code)
        self.assertEqual(data["product_id"], self.item.product_id)
        self.assertEqual(data["delta"], self.adjustment.delta)
        self.assertEqual(data["reason"], self.adjustment.reason)
        self.assertEqual(data["created_by"], self.adjustment.created_by)

    def test_variant_crud(self):
        """Variant 에 대한 GET/POST/PATCH/DELETE 흐름 테스트"""
        list_url = "/api/v1/inventory/variants/"
        detail_url = f"/api/v1/inventory/variants/{self.variant.variant_code}/"

        # --- GET list
        r_list = self.client.get(list_url)
        self.assertEqual(r_list.status_code, status.HTTP_200_OK)

        # --- POST create
        payload = {
            "product_id": self.item.product_id,
            "name": self.item.name,
            "option": "새옵션",
            "stock": 5,
            "price": 2000,
            "min_stock": 1
        }
        r_post = self.client.post(list_url, payload, format="json")
        self.assertEqual(r_post.status_code, status.HTTP_201_CREATED)
        new_code = r_post.data["variant_code"]
        self.assertTrue(ProductVariant.objects.filter(variant_code=new_code).exists())

        # --- GET detail
        r_get = self.client.get(detail_url)
        self.assertEqual(r_get.status_code, status.HTTP_200_OK)

        # --- PATCH 수정
        patch_payload = {"memo": "테스트메모"}
        r_patch = self.client.patch(detail_url, patch_payload, format="json")
        self.assertEqual(r_patch.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.memo, "테스트메모")

        # --- DELETE
        r_del = self.client.delete(detail_url)
        self.assertEqual(r_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductVariant.objects.filter(pk=self.variant.pk).exists())

    def test_variant_upload_excel(self):
        df = pd.DataFrame([{
            "상품코드": "PTEST02",
            "상품명": "테스트 상품 2",
            "상품 품목코드": "",
            "옵션": "색상 : 블랙",
            "판매가": 3000,
            "재고": 15,
            "판매수량": 3,
            "환불수량": 1
        }])
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        upload_file = SimpleUploadedFile("variants.xlsx", buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        url = "/api/v1/inventory/upload/"
        response = self.client.post(url, {"file": upload_file}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertIn("created_count", response.data)
        self.assertGreaterEqual(response.data["created_count"], 1)

    def test_sales_summary_upload_excel(self):
        df = pd.DataFrame([{
            "바코드": "PTEST03",
            "분류명": "식품",
            "상품명": "테스트 과자",
            "판매가": 1500,
            "매출건수": 2
        }])
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        upload_file = SimpleUploadedFile("sales_summary.xlsx", buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        url = "/api/v1/inventory/upload/"
        response = self.client.post(url, {"file": upload_file}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["type"], "sales_summary")
        self.assertIn("created_count", response.data)
        self.assertIn("updated_count", response.data)
        self.assertIn("errors", response.data)
        self.assertGreaterEqual(response.data["created_count"] + response.data["updated_count"], 1)

    def test_variant_merge(self):
        # 병합 대상 및 소스 생성
        variant1 = ProductVariant.objects.create(
            product=self.item, variant_code="PTEST01-002", option="색상 : 블랙", stock=5
        )
        variant2 = ProductVariant.objects.create(
            product=self.item, variant_code="PTEST01-003", option="색상 : 레드", stock=7
        )

        url = "/api/v1/inventory/variants/merge/"

        # ✅ 정상 병합 요청
        payload = {
            "target_variant_code": self.variant.variant_code,
            "source_variant_codes": [variant1.variant_code, variant2.variant_code]
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 204)
        self.assertTrue(ProductVariant.objects.filter(variant_code=self.variant.variant_code).exists())
        self.assertFalse(ProductVariant.objects.filter(variant_code=variant1.variant_code).exists())
        self.assertFalse(ProductVariant.objects.filter(variant_code=variant2.variant_code).exists())

        merged_variant = ProductVariant.objects.get(variant_code=self.variant.variant_code)
        expected_stock = self.variant.stock + variant1.stock + variant2.stock
        expected_adjustment = self.variant.adjustment + variant1.adjustment + variant2.adjustment

        self.assertEqual(merged_variant.stock, expected_stock)
        self.assertEqual(merged_variant.adjustment, expected_adjustment)


        # 예외 1: 대상 variant 자체가 없는 경우
        payload = {
            "target_variant_code": "NON_EXISTENT",
            "source_variant_codes": [self.variant.variant_code]
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

        # 예외 2: source variant 중 하나가 존재하지 않을 경우
        payload = {
            "target_variant_code": self.variant.variant_code,
            "source_variant_codes": ["INVALID_CODE"]
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

        # 예외 3: target 과 source 가 동일한 경우 (자기 자신을 병합)
        payload = {
            "target_variant_code": self.variant.variant_code,
            "source_variant_codes": [self.variant.variant_code]
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

        # 예외 4: source_variant_codes가 빈 리스트일 경우
        payload = {
            "target_variant_code": self.variant.variant_code,
            "source_variant_codes": []
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)