from django.urls import path
from .views import (
    ProductOptionListView,
    InventoryCategoryListView,
    ProductVariantDetailView,
    ProductVariantExportView,
    InventoryItemView,
    ProductVariantView,
    InventoryItemMergeView,
    ProductVariantCSVUploadView,
    StockUpdateView,
    InventoryRollbackView,
    InventoryAdjustmentListView,
    InventorySnapshotListCreateView,
    InventorySnapshotRetrieveView,
)

urlpatterns = [
    path("", ProductOptionListView.as_view(), name="inventory_options"),
    path("category", InventoryCategoryListView.as_view(), name="inventory-category"),
    path("variants/", ProductVariantView.as_view(), name="variant"),
    path("variants/export/", ProductVariantExportView.as_view(), name="variant_export"),
    path(
        "variants/merge/",
        InventoryItemMergeView.as_view(),
        name="inventoryitem-variant-merge",
    ),
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
        "upload/", ProductVariantCSVUploadView.as_view(), name="product-variant-upload"
    ),
    path(
        "rollback/<int:id>/", InventoryRollbackView.as_view(), name="inventory-rollback"
    ),
    path(
        "variants/stock/<str:variant_code>/",
        StockUpdateView.as_view(),
        name="stock-update",
    ),
    path("<str:product_id>/", InventoryItemView.as_view(), name="inventoryitem-detail"),
    path(
        "snapshot", InventorySnapshotListCreateView.as_view(), name="snapshot-list"
    ),  # GET /snapshot
    path(
        "snapshot/<int:id>/",
        InventorySnapshotRetrieveView.as_view(),
        name="snapshot-detail",
    ),  # GET /snapshot/{id}
]
