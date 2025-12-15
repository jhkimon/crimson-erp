import io
import pandas as pd
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.inventory.models import (
    InventoryItem,
    ProductVariant,
    InventoryAdjustment,
    ProductVariantStatus
)
from apps.inventory.utils.variant_code import generate_variant_code

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
        self.assertTrue(variant.variant_code.startswith("P00010-"))


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

class ProductVariantStatusPatchTest(APITestCase):

    def setUp(self):
        self.product = InventoryItem.objects.create(
            product_id="P00100",
            name="방패 필통",
            category="문구",
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_code="P00100000A",
            option="크림슨",
            stock=100,
        )

        self.status_obj = ProductVariantStatus.objects.create(
            year=2025,
            month=7,
            product=self.product,
            variant=self.variant,
            warehouse_stock_start=50,
            store_stock_start=30,
            inbound_quantity=20,
            store_sales=10,
            online_sales=5
        )

    def test_patch_variant_status_single_field(self):
        """
        PATCH - 단일 필드 수정
        """
        url = reverse(
            "variant-status-detail",
            args=[2025, 7, self.variant.variant_code],
        )

        payload = {
            "inbound_quantity": 99,
        }

        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.status_obj.refresh_from_db()
        self.assertEqual(self.status_obj.inbound_quantity, 99)

    def test_patch_variant_status_multiple_fields(self):
        """
        PATCH - 여러 필드 동시 수정
        """
        url = reverse(
            "variant-status-detail",
            args=[2025, 7, self.variant.variant_code],
        )

        payload = {
            "warehouse_stock_start": 60,
            "store_stock_start": 40,
            "store_sales": 25,
            "online_sales": 12,
        }

        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.status_obj.refresh_from_db()
        self.assertEqual(self.status_obj.warehouse_stock_start, 60)
        self.assertEqual(self.status_obj.store_stock_start, 40)
        self.assertEqual(self.status_obj.store_sales, 25)
        self.assertEqual(self.status_obj.online_sales, 12)

    def test_patch_variant_status_invalid_field_is_ignored(self):
        """
        PATCH - 허용되지 않은 필드는 무시되어야 함
        """
        url = reverse(
            "variant-status-detail",
            args=[2025, 7, self.variant.variant_code],
        )

        payload = {
            "inbound_quantity": 10,
            "year": 2030,            # ❌ 수정 불가
            "variant": "HACKED",     # ❌ 수정 불가
        }

        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.status_obj.refresh_from_db()
        self.assertEqual(self.status_obj.inbound_quantity, 10)
        self.assertEqual(self.status_obj.year, 2025)  # 변경 안 됨

    def test_patch_variant_status_not_found(self):
        """
        PATCH - 존재하지 않는 variant_status
        """
        url = reverse(
            "variant-status-detail",
            args=[2025, 7, "NOT_EXIST_CODE"],
        )

        payload = {
            "inbound_quantity": 10,
        }

        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class InventoryAdjustmentCreateTest(APITestCase):

    def setUp(self):
        self.product = InventoryItem.objects.create(
            product_id="P00900",
            name="방패 필통",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_code="P00900000A",
            option="블랙",
            stock=100,
            is_active=True,
        )

    def test_create_inventory_adjustment(self):
        """
        POST /inventory/adjustments/
        - InventoryAdjustment 생성
        - ProductVariantStatus 자동 생성
        """
        url = reverse("inventory-adjustments")

        payload = {
            "variant_code": self.variant.variant_code,
            "year": 2025,
            "month": 12,
            "delta": -7,
            "reason": "실사 재고 차이",
            "created_by": "관리자A",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # InventoryAdjustment 생성 확인
        adjustment = InventoryAdjustment.objects.get()
        self.assertEqual(adjustment.variant, self.variant)
        self.assertEqual(adjustment.delta, -7)
        self.assertEqual(adjustment.reason, "실사 재고 차이")
        self.assertEqual(adjustment.created_by, "관리자A")
        self.assertEqual(adjustment.year, 2025)
        self.assertEqual(adjustment.month, 12)

        # ProductVariantStatus 자동 생성 확인
        status_obj = ProductVariantStatus.objects.get(
            year=2025,
            month=12,
            variant=self.variant,
        )
        self.assertEqual(status_obj.product, self.product)

class InventoryAdjustmentWithExistingStatusTest(APITestCase):

    def setUp(self):
        self.product = InventoryItem.objects.create(
            product_id="P00910",
            name="삼방패 티셔츠",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_code="P00910000A",
            option="L",
            stock=50,
            is_active=True,
        )

        self.status = ProductVariantStatus.objects.create(
            year=2025,
            month=7,
            product=self.product,
            variant=self.variant,
        )

    def test_adjustment_does_not_create_duplicate_status(self):
        url = reverse("inventory-adjustments")

        payload = {
            "variant_code": self.variant.variant_code,
            "year": 2025,
            "month": 7,
            "delta": 5,
            "reason": "입고 누락 보정",
            "created_by": "관리자B",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # ProductVariantStatus는 여전히 1개
        self.assertEqual(
            ProductVariantStatus.objects.filter(
                year=2025,
                month=7,
                variant=self.variant,
            ).count(),
            1,
        )

class InventoryAdjustmentInactiveVariantTest(APITestCase):

    def setUp(self):
        product = InventoryItem.objects.create(
            product_id="P00920",
            name="방패 필통",
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            variant_code="P00920000A",
            option="화이트",
            stock=10,
            is_active=False,  # ❌ 비활성
        )

    def test_adjustment_with_inactive_variant_fails(self):
        url = reverse("inventory-adjustments")

        payload = {
            "variant_code": self.variant.variant_code,
            "delta": -1,
            "reason": "테스트",
            "created_by": "관리자",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ProductVariantExcelUploadBasicTest(APITestCase):
    """
    엑셀 업로드
    - 1행 업로드 시
      - ProductVariant 생성
      - ProductVariantStatus 생성
    """

    def _make_excel_file(self):
        """
        header=2 기준에 맞는 엑셀 파일 생성
        """
        # 실제 데이터 (3번째 줄부터)
        data = {
            "상품코드": ["P10000-A"],
            "오프라인 품목명": ["테스트 상품"],
            "온라인 품목명": ["테스트 상품 온라인"],
            "옵션": ["블랙"],
            "기말 재고": [100],
            "월초창고 재고": [40],
            "월초매장 재고": [30],
            "당월입고물량": [50],
            "매장 판매물량": [10],
            "쇼핑몰 판매물량": [10],
            "카테고리": ["문구"],
            "대분류": ["STORE"],
            "중분류": ["FASHION"],
            "설명": ["엑셀 업로드 테스트"],
        }


        df = pd.DataFrame(data)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            # 더미 행 2줄
            pd.DataFrame([[], []]).to_excel(
                writer, index=False, header=False
            )
            # 실제 데이터
            df.to_excel(
                writer, index=False, startrow=2
            )

        buffer.seek(0)
        return buffer

    def test_excel_upload_creates_variant_and_status(self):
        url = reverse("variant-excel-upload")

        excel_file = self._make_excel_file()

        upload_file = SimpleUploadedFile(
            "inventory.xlsx",
            excel_file.read(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

        response = self.client.post(
            url,
            data={"file": upload_file},
            format="multipart",
        )

        # API 성공
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Variant 생성 확인
        self.assertEqual(ProductVariant.objects.count(), 1)
        variant = ProductVariant.objects.first()
        self.assertEqual(variant.variant_code, "P10000-A")
        self.assertEqual(variant.stock, 100)

        # Product 생성 확인
        self.assertEqual(InventoryItem.objects.count(), 1)
        product = InventoryItem.objects.first()
        self.assertEqual(product.product_id, "P10000")

        # 월별 Status 생성 확인
        self.assertEqual(ProductVariantStatus.objects.count(), 1)
        status_obj = ProductVariantStatus.objects.first()
        self.assertEqual(status_obj.variant, variant)
        self.assertEqual(status_obj.warehouse_stock_start, 40)
        self.assertEqual(status_obj.store_stock_start, 30)

class ProductVariantCreateNoOptionTest(APITestCase):

    def test_create_variant_without_option(self):
        url = reverse("variant")
        payload = {
            "product_id": "P00011",
            "name": "옵션 없는 상품",
            "stock": 10,
            "price": 1000,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        variant = ProductVariant.objects.first()
        self.assertEqual(variant.variant_code, "P00011-DEFAULT")
        self.assertEqual(variant.option, "")

class VariantCodeUtilTest(APITestCase):

    def test_generate_variant_code_cases(self):
        self.assertEqual(
            generate_variant_code("P001", "", ""),
            "P001-DEFAULT"
        )
        self.assertEqual(
            generate_variant_code("P001", "화이트", ""),
            "P001-화이트".upper()
        )
        self.assertEqual(
            generate_variant_code("P001", "화이트", "M"),
            "P001-화이트-M".upper()
        )