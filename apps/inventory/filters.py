import django_filters
from django.db.models import F, ExpressionWrapper, IntegerField
from .models import ProductVariant, InventoryAdjustment, ProductVariantStatus

class ProductVariantFilter(django_filters.FilterSet):
    product_name = django_filters.CharFilter(method="filter_product_name")

    big_category = django_filters.BaseInFilter(
        field_name="product__big_category",
        lookup_expr="in"
    )
    middle_category = django_filters.BaseInFilter(
        field_name="product__middle_category",
        lookup_expr="in"
    )
    category = django_filters.BaseInFilter(
        field_name="product__category",
        lookup_expr="in"
    )

    class Meta:
        model = ProductVariant
        fields = [
            "product_name",
            "big_category",
            "middle_category",
            "category",
        ]

    def filter_product_name(self, queryset, name, value):
        return queryset.filter(product__name__icontains=value)

    
class InventoryAdjustmentFilter(django_filters.FilterSet):
    variant_code = django_filters.CharFilter(field_name='variant__variant_code', lookup_expr='exact')

    class Meta:
        model = InventoryAdjustment
        fields = ['variant_code']


class ProductVariantStatusFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter()
    month = django_filters.NumberFilter()
    product_code = django_filters.CharFilter(
        field_name="product__product_id", lookup_expr="icontains"
    )
    variant_code = django_filters.CharFilter(
        field_name="variant__variant_code", lookup_expr="icontains"
    )
    category = django_filters.CharFilter(
        field_name="product__category", lookup_expr="icontains"
    )

    class Meta:
        model = ProductVariantStatus
        fields = [
            "year",
            "month",
            "product_code",
            "variant_code",
            "category",
        ]
