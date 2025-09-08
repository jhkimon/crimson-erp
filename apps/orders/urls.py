from django.urls import path
from .views import OrderListView, OrderExportView, OrderDetailView

urlpatterns = [
    path("", OrderListView.as_view(), name="orders"),
    path("export/", OrderExportView.as_view(), name="order-export"),
    path("<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
]