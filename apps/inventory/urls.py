from django.urls import path
from .views import InventoryListView, ProductVariantDetailView

urlpatterns = [
    path("items/", InventoryListView.as_view(),
         name="inventory-list"),  # /api/v1/inventory/items/
    path("<int:variant_id>/", ProductVariantDetailView.as_view(),
         name="productvariant-detail")  # / api/v1/inventory/{variant_id}
]
