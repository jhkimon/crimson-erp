from django.urls import path
from .views import (
    ProductOptionListView,
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
    ProductMatchingView,
    ProductMergeView,
    MergeableProductsListView,
    BatchProductMergeView,
    ProductMergeCreateView,
)

urlpatterns = [
    path("", ProductOptionListView.as_view(), name="inventory_options"),
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
    path(
        "snapshot", InventorySnapshotListCreateView.as_view(), name="snapshot-list"
    ),  # GET /snapshot
    path(
        "snapshot/<int:id>/",
        InventorySnapshotRetrieveView.as_view(),
        name="snapshot-detail",
    ),  # GET /snapshot/{id}
    path("products/match/", ProductMatchingView.as_view(), name="product-matching"),
    path(
        "products/merge/<str:management_code>/",
        ProductMergeView.as_view(),
        name="product-merge",
    ),
    path("<str:product_id>/", InventoryItemView.as_view(), name="inventoryitem-detail"),
    # 병합 가능한 상품 목록
    path(
        "mergeable/products",
        MergeableProductsListView.as_view(),
        name="mergeable-products",
    ),  # GET /mergeable/products
    # 단일 상품 병합
    path(
        "merge/products", ProductMergeCreateView.as_view(), name="merge-products"
    ),  # POST /merge/products
    # 일괄 상품 병합
    path(
        "batch/merge/products",
        BatchProductMergeView.as_view(),
        name="batch-merge-products",
    ),  # POST /batch/merge/products
]
