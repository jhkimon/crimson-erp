# REST API
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# Swagger
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Serializer, Model
from ..serializers import (
    ProductVariantSerializer
)

from ..models import (
    ProductVariant
)

from django_filters.rest_framework import DjangoFilterBackend

from ..filters import ProductVariantFilter, InventoryAdjustmentFilter, ProductVariantStatusFilter



class ProductVariantExportView(APIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductVariantFilter
    ordering_fields = ["stock", "price"]

    @swagger_auto_schema(
        operation_summary="전체 상품 상세 정보 Export (엑셀용)",
        tags=["inventory - View"],
        manual_parameters=[
            openapi.Parameter("stock_lt", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("stock_gt", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("sales_min", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("sales_max", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                "product_name", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "category", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING
            ),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "channel",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="채널 필터 (online/offline)",
            ),
        ],
        responses={200: ProductVariantSerializer(many=True)},
    )
    def get(self, request):
        queryset = ProductVariant.objects.select_related("product").all()

        # filtering
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, self)

        # ordering
        ordering = request.query_params.get("ordering")
        if ordering:
            queryset = queryset.order_by(ordering)

        serializer = ProductVariantSerializer(queryset, many=True)
        return Response(serializer.data, status=200)
