from django.urls import path
from apps.supplier.views import SupplierListCreateView, SupplierRetrieveUpdateView

urlpatterns = [
    path('', SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('<int:pk>/', SupplierRetrieveUpdateView.as_view(), name='supplier-detail-update'),
]