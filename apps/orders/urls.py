from django.urls import path
from .views import OrderListView, OrderDetailView, OrderStatusView

urlpatterns = [
    # path("list/", OrderListView.as_view(), name="order-list"),
    path("orders/", OrderListView.as_view(), name="orders"),
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:order_id>/status/", OrderStatusView.as_view(), name="order-status-update"),
]