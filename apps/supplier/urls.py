from django.urls import path
from apps.supplier.views import SupplierListCreateView, SupplierRetrieveUpdateView, SupplierOrderDetailView

urlpatterns = [
    path('', SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('<int:pk>/', SupplierRetrieveUpdateView.as_view(), name='supplier-detail'),
    path('<int:pk>/orders/', SupplierOrderDetailView.as_view(), name='supplier-orders'),
]