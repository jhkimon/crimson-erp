from django.urls import path
from .views import (InventoryListView, ProductVariantDetailView, InventoryItemView, ProductVariantCreateView,
                    InventoryItemMergeView, InventoryAdjustmentListCreateView, StockUpdateView, InventoryExportView, POSWebhookView,
                    PaymentConfirmView, OrderCancelView, StockAvailabilityView, cleanup_expired_reservations)

urlpatterns = [
    path("items/", InventoryListView.as_view(),
         name="inventory-list"),  # /api/v1/inventory/items/
    path("items/variants/merge/", InventoryItemMergeView.as_view(),
         name="inventoryitem-variant-merge"),  # api/v1/inventory/items/variants/merge/
    path("items/<int:product_id>/", InventoryItemView.as_view(),
         name="inventoryitem-detail"),  # api/v1/inventory/items/{product_id}
    path("items/<int:product_id>/variants/", ProductVariantCreateView.as_view(),
         # api/v1/inventory/items/{product_id}/variants)
         name='productvariant-create'),
    path("items/<int:product_id>/variants/<int:variant_id>/", ProductVariantDetailView.as_view(),
         # / api/v1/inventory/items/{product_id}/variants/{variant_id}
         name="productvariant-detail"),

    path(
        "items/<int:product_id>/variants/<int:variant_id>/adjustments/",
        InventoryAdjustmentListCreateView.as_view(),
        name="variant-adjustment-list"
        # api/v1/inventory/items/{product_id}/variants/{variant_id}/adjustments/
    ),
    path('products/<int:product_id>/variants/<int:variant_id>/stock/',
         # api/v1/inventory/{product_id}/variants/{variant_id}/stock
         StockUpdateView.as_view(), name='stock-update'),
    path(
        'items/export/',
        InventoryExportView.as_view(),  # api/v1/inventory/items/export/
        name='inventory-export'
    ),
    # POS 연동 관련 엔드포인트
    path('pos/webhook/', POSWebhookView.as_view(), name='pos-webhook'),
    path('pos/payment-confirm/', PaymentConfirmView.as_view(),
         name='payment-confirm'),
    path('pos/cancel-order/', OrderCancelView.as_view(), name='cancel-order'),

    # 재고 관련
    path('stock/availability/', StockAvailabilityView.as_view(),
         name='stock-availability'),
    path('stock/cleanup-reservations/',
         cleanup_expired_reservations, name='cleanup-reservations'),
]
