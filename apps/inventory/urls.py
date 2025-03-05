from django.urls import path
from .views import InventoryListView

urlpatterns = [
    path("items/", InventoryListView.as_view(), name="inventory-list"),  # /api/v1/inventory/items/
]