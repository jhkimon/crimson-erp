from django.urls import path
from .views import InventoryListView, ProductOptionListView, InventoryItemView, ProductVariantCreateView, ProductVariantDetailView, ProductVariantCSVUploadView

urlpatterns = [
    path("", ProductOptionListView.as_view(), name='inventory_options'),
    path("items/", InventoryListView.as_view(),
         name="inventory-list"), 
    path("items/variants/", ProductVariantCreateView.as_view(), name="variant-create"),
    path("items/<str:product_id>/", InventoryItemView.as_view(),
         name="inventoryitem-detail"), 
    path("items/variants/<str:variant_id>/", ProductVariantDetailView.as_view(), name="variant-detail"),
    path("upload/", ProductVariantCSVUploadView.as_view(), name="product-variant-upload"),
]
