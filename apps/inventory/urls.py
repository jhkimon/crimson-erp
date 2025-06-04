from django.urls import path
from .views import InventoryListView, ProductVariantDetailView, InventoryItemView, ProductVariantCreateView

urlpatterns = [
    path("items/", InventoryListView.as_view(),
         name="inventory-list"), 
    path("items/<int:product_id>/", InventoryItemView.as_view(),
         name="inventoryitem-detail"), 
    path("items/<int:product_id>/variants/", ProductVariantCreateView.as_view(),
         name='productvariant-create'),
    path("items/<int:product_id>/variants/<int:variant_id>/", ProductVariantDetailView.as_view(),
         name="productvariant-detail"),
]
