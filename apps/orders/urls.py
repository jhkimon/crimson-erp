from django.urls import path
from .views import OrderListView
urlpatterns = [
    path("list/", OrderListView.as_view(), name="order-list"), 
]