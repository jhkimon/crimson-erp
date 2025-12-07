from django.urls import path
from .views import (
    # QuickView
    ProductOptionListView,
    InventoryCategoryListView,
    InventoryItemView,
    # ProductVariant
    ProductVariantView,
    ProductVariantDetailView,
    ProductVariantExportView,
    # Adjustment
    StockUpdateView,
    InventoryAdjustmentListView
)

urlpatterns = [
    path("", ProductOptionListView.as_view(), name="inventory_options"),
    path("category/", InventoryCategoryListView.as_view(), name="inventory-category"),
    path("variants/", ProductVariantView.as_view(), name="variant"),
    path("variants/export/", ProductVariantExportView.as_view(), name="variant_export"),
    path(
        "adjustments/",
        InventoryAdjustmentListView.as_view(),
        name="inventory-adjustments",
    ),
    path(
        "variants/<str:variant_code>/",
        ProductVariantDetailView.as_view(),
        name="variant-detail",
    ),
    path(
        "variants/stock/<str:variant_code>/",
        StockUpdateView.as_view(),
        name="stock-update",
    ),
        path("<str:product_id>/", InventoryItemView.as_view(), name="inventoryitem-detail"),
]
