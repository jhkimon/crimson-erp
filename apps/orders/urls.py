from django.urls import path
from .views import OrderListView, OrderDetailView, OrderStatusView

urlpatterns = [
    path("", OrderListView.as_view(), name="orders"),
    path("<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:order_id>/status/", OrderStatusView.as_view(), name="order-status-update"),
]