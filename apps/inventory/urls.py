from django.urls import path
from .views import InventoryListView, ProductVariantDetailView, InventoryItemView

urlpatterns = [
    path("items/", InventoryListView.as_view(),
         name="inventory-list"), 
    path("items/<str:product_id>/", InventoryItemView.as_view(),
         name="inventoryitem-detail"), 
    path("items/variants/<str:variant_id>/", ProductVariantDetailView.as_view(),
         name="productvariant-detail"),
]
