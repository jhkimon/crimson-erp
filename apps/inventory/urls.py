from django.urls import path
from .views import (ProductOptionListView, ProductVariantDetailView, ProductVariantExportView, InventoryItemView, ProductVariantView,
                    InventoryItemMergeView, ProductVariantCSVUploadView, StockUpdateView, InventoryAdjustmentListView)

urlpatterns = [
    path("", ProductOptionListView.as_view(), name='inventory_options'),
    path("variants/", ProductVariantView.as_view(), name="variant"),
    path("variants/export/", ProductVariantExportView.as_view(), name="variant_export"),
    path("variants/merge/", InventoryItemMergeView.as_view(),name="inventoryitem-variant-merge"), 
    path("adjustments/", InventoryAdjustmentListView.as_view(), name="inventory-adjustments"),
    path("variants/<str:variant_code>/", ProductVariantDetailView.as_view(), name="variant-detail"),
    path("upload/", ProductVariantCSVUploadView.as_view(), name="product-variant-upload"),
    path('variants/stock/<str:variant_code>/', StockUpdateView.as_view(), name='stock-update'),
    path("<str:product_id>/", InventoryItemView.as_view(),
         name="inventoryitem-detail"), 
]
