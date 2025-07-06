from django.urls import path
from apps.supplier.views import SupplierListCreateView, SupplierRetrieveUpdateView,  SupplierVariantUpdateView

urlpatterns = [
    path('', SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('<int:pk>/', SupplierRetrieveUpdateView.as_view(), name='supplier-detail'),
    path('variant/<int:pk>/', SupplierVariantUpdateView.as_view(), name='supplier-variant-update'),
]