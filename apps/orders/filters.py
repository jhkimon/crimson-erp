import django_filters
from django.db.models import Q
from apps.orders.models import Order

class OrderFilter(django_filters.FilterSet):
    product_name = django_filters.CharFilter(method='filter_by_product_name')
    supplier = django_filters.CharFilter(field_name='supplier__name', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='exact')
    start_date = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')

    class Meta:
        model = Order
        fields = ['product_name', 'supplier', 'status', 'start_date', 'end_date']

    def filter_by_product_name(self, queryset, name, value):
        return queryset.filter(items__variant__product__name__icontains=value).distinct()