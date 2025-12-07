from django.urls import path
from .views import (
    # QuickView
    ProductOptionListView,
    InventoryCategoryListView,
    InventoryItemView,
    # Upload
    ProductVariantExcelUploadView,
    # ProductVariant
    ProductVariantView,
    ProductVariantDetailView,
    ProductVariantExportView,
    # Adjustment
    StockUpdateView,
    InventoryAdjustmentListView,
    # 엑셀대응
    ProductVariantStatusListView
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
        "variants/upload-excel/",
        ProductVariantExcelUploadView.as_view(),
        name="variant-excel-upload",
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
    path(
        "variant-status/",
        ProductVariantStatusListView.as_view(),
        name="variant-status-list",
    ),
    path("<str:product_id>/", InventoryItemView.as_view(), name="inventoryitem-detail"),
]
