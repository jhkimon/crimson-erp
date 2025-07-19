import io
from django.db import transaction
from django.http import HttpResponse
import openpyxl
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import InventoryItem, ProductVariant, InventoryAdjustment, SalesChannel, SalesTransaction, SalesTransactionItem, StockReservation
from .serializers import InventoryItemSerializer, ProductVariantSerializer, InventoryAdjustmentSerializer

logger = logging.getLogger(__name__)

# 재고 전체 목록 작업 (조회 및 추가)


class InventoryListView(APIView):
    """
    GET: 전체 제품 목록 조회
    POST: 새로운 제품 추가
    """

    permission_classes = [AllowAny]  # 테스트용 jwt면제
    # 전체 목록 조회

    @swagger_auto_schema(
        operation_summary="전체 제품 목록 조회",
        operation_description="현재 등록된 모든 제품 목록을 조회합니다.",
        responses={200: InventoryItemSerializer(many=True)}
    )
    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemSerializer(items, many=True)
        return Response(serializer.data)

    # 신규 상품 추가
    @swagger_auto_schema(
        operation_summary="새로운 제품 추가",
        operation_description="새로운 제품을 등록합니다.",
        request_body=InventoryItemSerializer,
        responses={201: InventoryItemSerializer}
    )
    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 개별 제품 관련 작업 (조회/수정/삭제)


class InventoryItemView(APIView):
    '''
    GET: 특정 상품 기본 정보 조회 (상품코드, 상품명, 생성일자)
    PUT: 상품 기본 정보 수정
    DELETE: 상품 삭제
    '''
    permission_classes = [AllowAny]

    # 상품 기본 정보 조회
    @swagger_auto_schema(
        operation_summary="특정 상품 기본 정보 조회",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품의 기본 정보를 조회합니다",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_INTEGER
        )],
        responses={200: InventoryItemSerializer, 404: "Not Found"})
    def get(self, request, product_id: int):
        try:
            item = InventoryItem.objects.get(id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InventoryItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 상품 기본 정보 수정
    @swagger_auto_schema(
        operation_summary="특정 상품 기본 정보 수정",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품의 기본 정보를 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="수정할 상품의 product_id",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=InventoryItemSerializer,
        responses={200: InventoryItemSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, product_id: int):
        try:
            item = InventoryItem.objects.get(id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InventoryItemSerializer(item, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="특정 상품 삭제",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품을 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="삭제할 상품의 product_id",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={204: "삭제 완료: Successfully Deleted", 404: "Not Found"}
    )
    def delete(self, request, product_id: int):
        try:
            item = InventoryItem.objects.get(id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 상품 상세 정보 CRUD


class ProductVariantCreateView(APIView):
    """
    POST: 특정 상품의 상세 정보 생성
    """
    permission_classes = [AllowAny]
    # 상품 상세 정보 추가

    @swagger_auto_schema(
        operation_summary="특정 상품에 새로운 상세 정보 추가",
        operation_description="URL 파라미터로 전달된 product_id에 해당하는 상품의 상세 정보를 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id",
                in_=openapi.IN_PATH,
                description="상세 정보를 추가할 상품의 product_id",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=ProductVariantSerializer,
        responses={201: ProductVariantSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def post(self, request, product_id: int):
        try:
            product = InventoryItem.objects.get(id=product_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "상품 기본 정보가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(
            data=request.data, context={'request': request, 'product': product})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductVariantDetailView(APIView):
    """
    GET: 특정 상품의 상세 정보 조회 (상세코드, 옵션, 재고량, 가격, 생성일자, 수정일자자)
    PUT: 특정 상품 상세 정보 수정
    DELETE: 특정 상품 상세 정보 삭제
    """

    permission_classes = [AllowAny]

    # 제품 상세 정보 조회

    @swagger_auto_schema(operation_summary="특정 상품의 상세 정보 조회",
                         operation_description="URL 파라미터로 전달된 variant_id에 해당하는 특정 상품의 상세 정보를 조회합니다.",
                         manual_parameters=[openapi.Parameter(
                             name="product_id",
                             in_=openapi.IN_PATH,
                             description="조회할 상품의 product_id",
                             type=openapi.TYPE_INTEGER
                         ),
                             openapi.Parameter(
                                 name="variant_id",
                                 in_=openapi.IN_PATH,
                                 description="조회할 상품의 variant_id",
                                 type=openapi.TYPE_INTEGER
                         )
                         ],
                         responses={200: ProductVariantSerializer, 404: "Not Found"})
    def get(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 제품 상세 정보 수정
    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 수정",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 특정 상품의 상세 정보를 수정합니다.",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_INTEGER
        ),
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 상품의 variant_id",
                type=openapi.TYPE_INTEGER
        )
        ],
        request_body=ProductVariantSerializer,
        responses={200: ProductVariantSerializer,
                   400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductVariantSerializer(
            variant, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # patch를 이용한 제품 정보 수정
    ''' 
    @swagger_auto_schema(
        operation_summary="특정 품목 부분 수정",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 제품 변형 정보를 부분적으로 수정합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="수정할 제품 변형(variant)의 ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=ProductVariantSerializer,
        responses={200: ProductVariantSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def patch(self, request, variant_id: int):
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # partial=True를 통해 부분 업데이트를 허용합니다.
        serializer = ProductVariantSerializer(variant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    '''

    # 상품 상세 정보 삭제

    @swagger_auto_schema(
        operation_summary="특정 상품의 상세 정보 삭제",
        operation_description="URL 파라미터로 전달된 variant_id에 해당하는 상품의 상세세 정보를 삭제합니다.",
        manual_parameters=[openapi.Parameter(
            name="product_id",
            in_=openapi.IN_PATH,
            description="조회할 상품의 product_id",
            type=openapi.TYPE_INTEGER
        ),
            openapi.Parameter(
                name="variant_id",
                in_=openapi.IN_PATH,
                description="삭제할 상품의 variant_id",
                type=openapi.TYPE_INTEGER
        )
        ],
        responses={204: "삭제 완료: Successfully Deleted", 404: "Not Found"}
    )
    def delete(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "상세 정보가 존재하지 않습니다"}, status=status.HTTP_404_NOT_FOUND)

        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 동일 상품 다른 id 하나로 병합하기


class InventoryItemMergeView(APIView):
    """
    POST: 동일 상품이지만 id가 다른 상품을 하나로 병합용
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 코드 병합",
        operation_description="여러 variant(source_variant_codes)를 target_variant_code로 병합합니다. 병합된 variant들은 삭제되고, 연관된 product도 통합됩니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["target_variant_code", "source_variant_codes"],
            properties={
                "target_variant_code": openapi.Schema(type=openapi.TYPE_STRING, description="최종 남길 variant_code"),
                "source_variant_codes": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="합칠(삭제할) variant_code 리스트"
                )
            }
        ),
        responses={204: "Merge completed.",
                   400: "Bad Request", 404: "Not Found"}
    )
    def post(self, request):
        target_variant_code = request.data.get(
            "target_variant_code")  # 병합 대상 variant_code (최종적으로 남는 코드)
        # 병합 필요 variant_code (fade out되는 코드들)
        source_variant_codes = request.data.get("source_variant_codes")

        if not isinstance(source_variant_codes, list) or not target_variant_code:
            return Response({"error": "target_variant_code와 source_variant_codes(리스트)를 모두 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure target variant exists
        try:
            target_variant = ProductVariant.objects.get(
                variant_code=target_variant_code)
        except ProductVariant.DoesNotExist:
            return Response({"error": "target_variant_code에 해당하는 variant가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        # Exclude target from sources if accidentally included
        source_variant_codes = [
            code for code in source_variant_codes if code != target_variant_code]
        source_variants = ProductVariant.objects.filter(
            variant_code__in=source_variant_codes)

        if not source_variants.exists():
            return Response({"error": "합칠 source_variant_codes에 유효한 variant가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # Execute merge within transaction
        with transaction.atomic():
            # 1) 모든 source variant들의 데이터를 target variant로 병합
            self._merge_variant_data(target_variant, source_variants)

            # 2) Source variant들과 연관된 product 정리
            self._cleanup_orphaned_products(
                source_variants, target_variant.product)

            # 3) Source variant들 삭제
            source_variants.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _merge_variant_data(self, target_variant, source_variants):
        """
        Source variant들의 데이터를 target variant로 병합
        """
        # 재고 합산
        total_stock = target_variant.stock
        total_reserved_stock = target_variant.reserved_stock
        total_adjustment = target_variant.adjustment

        for source_variant in source_variants:
            total_stock += source_variant.stock
            total_reserved_stock += source_variant.reserved_stock
            total_adjustment += source_variant.adjustment

        # Target variant 업데이트
        target_variant.stock = total_stock
        target_variant.reserved_stock = total_reserved_stock
        target_variant.adjustment = total_adjustment
        target_variant.save()

        # 재고 조정 기록들을 target variant로 이동
        from .models import InventoryAdjustment
        InventoryAdjustment.objects.filter(
            variant__in=source_variants
        ).update(variant=target_variant)

        # 판매 트랜잭션 아이템들을 target variant로 이동
        from .models import SalesTransactionItem
        SalesTransactionItem.objects.filter(
            variant__in=source_variants
        ).update(variant=target_variant)

        # 재고 예약들을 target variant로 이동
        from .models import StockReservation
        StockReservation.objects.filter(
            variant__in=source_variants
        ).update(variant=target_variant)

        # 외래키 참조하는 다른 테이블들을 target variant로 이동
        from django.db import connection
        with connection.cursor() as cursor:
            source_variant_ids = [str(v.id) for v in source_variants]
            if source_variant_ids:
                # order_items 테이블 업데이트 (다른 앱에 있는 테이블)
                cursor.execute(
                    f"UPDATE order_items SET variant_id = %s WHERE variant_id IN ({','.join(['%s'] * len(source_variant_ids))})",
                    [target_variant.id] + source_variant_ids
                )

                # supplier_suppliervariant 테이블 업데이트
                cursor.execute(
                    f"UPDATE supplier_suppliervariant SET variant_id = %s WHERE variant_id IN ({','.join(['%s'] * len(source_variant_ids))})",
                    [target_variant.id] + source_variant_ids
                )

    def _cleanup_orphaned_products(self, source_variants, target_product):
        """
        Source variant들이 삭제된 후 고아가 되는 product들을 정리
        """
        # Source variant들의 product들을 찾음
        source_products = set()
        for variant in source_variants:
            if variant.product.id != target_product.id:
                source_products.add(variant.product)

        # 각 source product가 다른 variant를 가지고 있는지 확인
        for product in source_products:
            # 현재 삭제될 variant들을 제외한 다른 variant가 있는지 확인
            remaining_variants = ProductVariant.objects.filter(
                product=product
            ).exclude(id__in=[v.id for v in source_variants])

            # 다른 variant가 없으면 product 비활성화
            if not remaining_variants.exists():
                product.is_active = False
                product.save()

# 상품 재고 임시 조정용 값 생성하기


class InventoryAdjustmentListCreateView(APIView):
    """
    GET: 특정 변형의 재고 조정 이력 조회
    POST: 새로운 재고 조정 레코드 생성, 실제로 차이나는 수치를 입력합니다. (예: 10개 더 많으면 10, 더 적으면 -10을 입력)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="재고 조정 이력 조회",
        operation_description="특정 variant_id에 해당하는 재고 조정 이력을 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id", in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER, description="상품 ID"
            ),
            openapi.Parameter(
                name="variant_id", in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER, description="variant ID"
            )
        ],
        responses={200: InventoryAdjustmentSerializer(
            many=True), 404: "Not Found"}
    )
    def get(self, request, product_id: int, variant_id: int):
        adjustments = InventoryAdjustment.objects.filter(variant_id=variant_id)
        serializer = InventoryAdjustmentSerializer(adjustments, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="재고 조정 생성",
        operation_description="재고가 일치하지 않을 때 임시로 조정값을 기록합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="product_id", in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER, description="상품 ID"
            ),
            openapi.Parameter(
                name="variant_id", in_=openapi.IN_PATH,
                type=openapi.TYPE_INTEGER, description="variant ID"
            )
        ],
        request_body=InventoryAdjustmentSerializer,
        responses={201: InventoryAdjustmentSerializer, 400: "Bad Request"}
    )
    def post(self, request, product_id: int, variant_id: int):
        # variant 존재 확인
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=404)

        data = request.data.copy()
        data['variant_id'] = variant_id  # URL에서 받은 variant_id 자동 설정

        serializer = InventoryAdjustmentSerializer(data=data)
        if serializer.is_valid():
            adjustment = serializer.save()
            # variant 모델의 adjustment 필드 업데이트
            variant.adjustment += adjustment.delta
            variant.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 재고 업데이트 전용
class StockUpdateView(APIView):
    """
    PUT: 재고량 직접 업데이트 (이력 추적 포함)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="재고량 직접 업데이트",
        operation_description="실사 재고량을 입력하여 재고를 업데이트하고 조정 이력을 자동 생성합니다.",
        manual_parameters=[
            openapi.Parameter(name="product_id",
                              in_=openapi.IN_PATH, type=openapi.TYPE_INTEGER),
            openapi.Parameter(name="variant_id",
                              in_=openapi.IN_PATH, type=openapi.TYPE_INTEGER)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['actual_stock'],
            properties={
                'actual_stock': openapi.Schema(type=openapi.TYPE_INTEGER, description="실사한 실제 재고량"),
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description="조정 사유"),
                'updated_by': openapi.Schema(type=openapi.TYPE_STRING, description="작업자")
            }
        ),
        responses={200: "Stock updated successfully", 404: "Not Found"}
    )
    def put(self, request, product_id: int, variant_id: int):
        try:
            variant = ProductVariant.objects.get(
                id=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=404)

        actual_stock = request.data.get('actual_stock')
        if actual_stock is None:
            return Response({"error": "actual_stock is required"}, status=400)

        if actual_stock < 0:
            return Response({"error": "actual_stock cannot be negative"}, status=400)

        # 현재 총 재고량 (stock + adjustment)
        current_total_stock = variant.stock + variant.adjustment
        delta = actual_stock - current_total_stock

        # 조정이 필요한 경우에만 처리
        if delta != 0:
            # 조정 이력 생성 (감사 추적용)
            InventoryAdjustment.objects.create(
                variant=variant,
                delta=delta,
                reason=request.data.get('reason', '재고 실사'),
                created_by=request.data.get('updated_by', 'unknown')
            )

            # stock을 실제 재고로 업데이트, adjustment는 0으로 리셋
            variant.stock = actual_stock
            variant.adjustment = 0
            variant.save()

            return Response({
                "message": "재고 업데이트 완료",
                "previous_total_stock": current_total_stock,
                "new_stock": actual_stock,
                "adjustment_delta": delta,
                "updated_at": variant.updated_at
            }, status=200)
        else:
            return Response({
                "message": "조정 불필요 - 재고가 일치합니다",
                "current_stock": current_total_stock
            }, status=200)

# 재고 요약 정보 엑셀로 제공하기


class InventoryExportView(APIView):
    """
    GET: 전체 재고 관리 요약을 엑셀(.xlsx) 파일로 다운로드
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="재고 관리 엑셀 다운로드",
        operation_description="전체 InventoryItem과 관련 Variants 정보를 엑셀 파일로 제공합니다.",
        responses={
            200: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    )
    def get(self, request):
        # 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Inventory Summary'

        # 헤더 작성
        headers = [
            'Product ID', 'Product Code', 'Name', 'Category',
            'Variant ID', 'Variant Code', 'Option',
            'Stock', 'Adjustment', 'Price'
        ]
        ws.append(headers)

        # 데이터 rows
        for item in InventoryItem.objects.filter(is_active=True):
            for var in item.variants.all():
                row = [
                    item.id, item.product_code, item.name, item.category,
                    var.id, var.variant_code, var.option,
                    var.stock, var.adjustment, var.price
                ]
                ws.append(row)

        # 메모리 버퍼에 저장
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # 응답
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=재고 정보 요약.xlsx'
        return response


# POS 대응용 로직들
class POSWebhookView(APIView):
    """
    온라인 POS에서 주문 발생시 호출되는 웹훅 엔드포인트
    """
    permission_classes = [AllowAny]  # API 키 검증은 별도로 구현

    @swagger_auto_schema(
        operation_summary="POS 주문 웹훅",
        operation_description="온라인 POS에서 주문이 발생했을 때 호출되는 엔드포인트",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["order_id", "items", "channel_id"],
            properties={
                "order_id": openapi.Schema(type=openapi.TYPE_STRING),
                "channel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "customer_name": openapi.Schema(type=openapi.TYPE_STRING),
                "customer_phone": openapi.Schema(type=openapi.TYPE_STRING),
                "items": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "variant_code": openapi.Schema(type=openapi.TYPE_STRING),
                            "quantity": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "unit_price": openapi.Schema(type=openapi.TYPE_INTEGER)
                        }
                    )
                )
            }
        )
    )
    def post(self, request):
        try:
            with transaction.atomic():
                # 주문 정보 파싱
                order_id = request.data.get('order_id')
                channel_id = request.data.get('channel_id')
                items = request.data.get('items', [])

                # 채널 확인
                try:
                    channel = SalesChannel.objects.get(
                        id=channel_id, is_active=True)
                except SalesChannel.DoesNotExist:
                    return Response(
                        {"error": "유효하지 않은 채널입니다"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 중복 주문 확인
                if SalesTransaction.objects.filter(external_order_id=order_id).exists():
                    return Response(
                        {"error": "이미 처리된 주문입니다"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 재고 확인
                stock_check_errors = []
                for item_data in items:
                    try:
                        variant = ProductVariant.objects.get(
                            variant_code=item_data['variant_code']
                        )
                        if variant.available_stock < item_data['quantity']:
                            stock_check_errors.append(
                                f"{variant.variant_code}: 재고 부족 "
                                f"(요청: {item_data['quantity']}, 가능: {variant.available_stock})"
                            )
                    except ProductVariant.DoesNotExist:
                        stock_check_errors.append(
                            f"존재하지 않는 상품: {item_data['variant_code']}"
                        )

                if stock_check_errors:
                    return Response(
                        {"error": "재고 확인 실패", "details": stock_check_errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 주문 생성
                total_amount = sum(
                    item['quantity'] * item['unit_price'] for item in items
                )

                transaction_obj = SalesTransaction.objects.create(
                    external_order_id=order_id,
                    channel=channel,
                    customer_name=request.data.get('customer_name', ''),
                    customer_phone=request.data.get('customer_phone', ''),
                    total_amount=total_amount,
                    status='pending'
                )

                # 주문 상품들과 재고 예약 생성
                for item_data in items:
                    variant = ProductVariant.objects.get(
                        variant_code=item_data['variant_code']
                    )

                    # 주문 상품 생성
                    transaction_item = SalesTransactionItem.objects.create(
                        transaction=transaction_obj,
                        variant=variant,
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price']
                    )

                    # 재고 예약 (30분간 유효)
                    StockReservation.objects.create(
                        variant=variant,
                        transaction_item=transaction_item,
                        reserved_quantity=item_data['quantity'],
                        expires_at=timezone.now() + timedelta(minutes=30)
                    )

                    # 예약 재고 업데이트
                    variant.reserved_stock += item_data['quantity']
                    variant.save()

                    transaction_item.is_stock_reserved = True
                    transaction_item.save()

                logger.info(f"POS 주문 처리 완료: {order_id}")
                return Response({
                    "message": "주문이 성공적으로 처리되었습니다",
                    "transaction_id": transaction_obj.id
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"POS 웹훅 처리 중 오류: {str(e)}")
            return Response(
                {"error": "주문 처리 중 오류가 발생했습니다"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentConfirmView(APIView):
    """
    결제 완료 확인 엔드포인트
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="결제 완료 확인",
        operation_description="온라인 POS에서 결제가 완료되었을 때 호출",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["order_id"],
            properties={
                "order_id": openapi.Schema(type=openapi.TYPE_STRING),
                "payment_method": openapi.Schema(type=openapi.TYPE_STRING),
                "paid_amount": openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        )
    )
    def post(self, request):
        order_id = request.data.get('order_id')

        try:
            with transaction.atomic():
                # 주문 조회
                transaction_obj = SalesTransaction.objects.get(
                    external_order_id=order_id,
                    status='pending'
                )

                # 재고 예약을 실제 차감으로 변환
                for item in transaction_obj.items.all():
                    reservation = StockReservation.objects.get(
                        transaction_item=item
                    )

                    # 실제 재고 차감
                    variant = item.variant
                    variant.stock -= item.quantity
                    variant.reserved_stock -= item.quantity
                    variant.save()

                    # 예약 확정
                    reservation.is_confirmed = True
                    reservation.save()

                    item.is_stock_deducted = True
                    item.save()

                # 주문 상태 업데이트
                transaction_obj.status = 'paid'
                transaction_obj.save()

                logger.info(f"결제 완료 처리: {order_id}")
                return Response({
                    "message": "결제가 성공적으로 확인되었습니다"
                })

        except SalesTransaction.DoesNotExist:
            return Response(
                {"error": "해당 주문을 찾을 수 없습니다"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"결제 확인 처리 중 오류: {str(e)}")
            return Response(
                {"error": "결제 확인 처리 중 오류가 발생했습니다"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderCancelView(APIView):
    """
    주문 취소 엔드포인트
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="주문 취소",
        operation_description="미결제 주문을 취소하고 예약 재고를 해제합니다",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["order_id"],
            properties={
                "order_id": openapi.Schema(type=openapi.TYPE_STRING),
                "cancel_reason": openapi.Schema(type=openapi.TYPE_STRING)
            }
        )
    )
    def post(self, request):
        order_id = request.data.get('order_id')

        try:
            with transaction.atomic():
                transaction_obj = SalesTransaction.objects.get(
                    external_order_id=order_id,
                    status='pending'
                )

                # 예약 재고 해제
                for item in transaction_obj.items.all():
                    try:
                        reservation = StockReservation.objects.get(
                            transaction_item=item
                        )

                        variant = item.variant
                        variant.reserved_stock -= item.quantity
                        variant.save()

                        reservation.delete()
                    except StockReservation.DoesNotExist:
                        pass

                # 주문 상태 업데이트
                transaction_obj.status = 'cancelled'
                transaction_obj.save()

                return Response({
                    "message": "주문이 성공적으로 취소되었습니다"
                })

        except SalesTransaction.DoesNotExist:
            return Response(
                {"error": "해당 주문을 찾을 수 없습니다"},
                status=status.HTTP_404_NOT_FOUND
            )


class StockAvailabilityView(APIView):
    """
    실시간 재고 확인 API
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="실시간 재고 확인",
        operation_description="상품별 실시간 재고 상태를 확인합니다",
        manual_parameters=[
            openapi.Parameter(
                name="variant_codes",
                in_=openapi.IN_QUERY,
                description="쉼표로 구분된 variant_code 목록",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def get(self, request):
        variant_codes = request.GET.get('variant_codes', '').split(',')

        if not variant_codes or variant_codes == ['']:
            return Response(
                {"error": "variant_codes 파라미터가 필요합니다"},
                status=status.HTTP_400_BAD_REQUEST
            )

        stock_info = []
        for code in variant_codes:
            try:
                variant = ProductVariant.objects.get(variant_code=code.strip())
                stock_info.append({
                    "variant_code": variant.variant_code,
                    "product_name": variant.product.name,
                    "option": variant.option,
                    "total_stock": variant.stock,
                    "reserved_stock": variant.reserved_stock,
                    "available_stock": variant.available_stock,
                    "price": variant.price
                })
            except ProductVariant.DoesNotExist:
                stock_info.append({
                    "variant_code": code.strip(),
                    "error": "상품을 찾을 수 없습니다"
                })

        return Response({"stock_info": stock_info})


@api_view(['POST'])
@permission_classes([AllowAny])
def cleanup_expired_reservations(request):
    """
    만료된 재고 예약을 정리하는 배치 작업 엔드포인트
    """
    try:
        with transaction.atomic():
            # 만료된 예약들 조회
            expired_reservations = StockReservation.objects.filter(
                expires_at__lt=timezone.now(),
                is_confirmed=False
            )

            cleaned_count = 0
            for reservation in expired_reservations:
                # 예약 재고 해제
                variant = reservation.variant
                variant.reserved_stock = max(0,
                                             variant.reserved_stock - reservation.reserved_quantity
                                             )
                variant.save()

                # 관련 주문을 취소 상태로 변경
                transaction_obj = reservation.transaction_item.transaction
                if transaction_obj.status == 'pending':
                    transaction_obj.status = 'cancelled'
                    transaction_obj.save()

                reservation.delete()
                cleaned_count += 1

            return Response({
                "message": f"{cleaned_count}개의 만료된 예약이 정리되었습니다"
            })

    except Exception as e:
        logger.error(f"예약 정리 중 오류: {str(e)}")
        return Response(
            {"error": "예약 정리 중 오류가 발생했습니다"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
