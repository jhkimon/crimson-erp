from django.urls import path
from .views import InventoryListView, ProductVariantDetailView, InventoryItemView, ProductVariantCreateView

urlpatterns = [
    path("items/", InventoryListView.as_view(),
         name="inventory-list"),  # /api/v1/inventory/items/
    path("items/<int:product_id>/", InventoryItemView.as_view(),
         name="inventoryitem-detail"),  # api/v1/inventory/items/{product_id}
    path("items/<int:product_id>/variants/", ProductVariantCreateView.as_view(),
         # api/v1/inventory/items/{product_id}/variants)
         name='productvariant-create'),
    path("items/<int:product_id>/variants/<int:variant_id>/", ProductVariantDetailView.as_view(),
         # / api/v1/inventory/items/{product_id}/variants/{variant_id}
         name="productvariant-detail"),
]
