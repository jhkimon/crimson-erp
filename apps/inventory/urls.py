from django.urls import path
from .views import (
    # QuickView
    ProductOptionListView,
    InventoryCategoryListView,
    InventoryItemView,
    ProductCategoryView,
    ProductListSimpleView,
    # Upload
    ProductVariantExcelUploadView,
    # ProductVariant
    ProductVariantView,
    ProductVariantDetailView,
    ProductVariantExportView,
    # Adjustment
    InventoryAdjustmentView,
    # ProductVariantStatus
    ProductVariantStatusListView,
    ProductVariantStatusDetailView,
    ProductVariantStatusBulkUpdateView,
    ProductVariantStatusCreateView,
    SyncInboundFromOrdersView
)

urlpatterns = [
    path("", ProductOptionListView.as_view(), name="inventory_options"),
    path(
        "products/",
        ProductListSimpleView.as_view(),
        name="inventory-product-list"
    ),
    path(
        "products/<str:product_id>/categories/",
        ProductCategoryView.as_view(),
        name="inventory-product-category"
    ),
    path("category/", InventoryCategoryListView.as_view(), name="inventory-category"),
    path("variants/", ProductVariantView.as_view(), name="variant"),
    path("variants/export/", ProductVariantExportView.as_view(), name="variant-export"),
    path(
        "adjustments/",
        InventoryAdjustmentView.as_view(),
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
        "variant-status/",
        ProductVariantStatusListView.as_view(),
        name="variant-status-list",
    ),
    path(
    "variant-status/<int:year>/<int:month>/<str:variant_code>/",
    ProductVariantStatusDetailView.as_view(),
    name="variant-status-detail",
    ),
    path(
    "variant-status/<int:year>/<int:month>",
    ProductVariantStatusCreateView.as_view(),
    ),
    path(
    "variant-status/bulk",
    ProductVariantStatusBulkUpdateView.as_view(),
    name="variant-status-bulk"
    ),
    path(
        "variant-status/sync-inbound/<int:year>/<int:month>/",
        SyncInboundFromOrdersView.as_view(),
        name="inventory-sync-inbound",
    ),
    path("<str:product_id>/", InventoryItemView.as_view(), name="inventoryitem-detail"),
]
