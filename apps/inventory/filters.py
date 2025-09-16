import django_filters
from django.db.models import F, ExpressionWrapper, IntegerField
from .models import ProductVariant, InventoryAdjustment

class ProductVariantFilter(django_filters.FilterSet):
    stock_lt = django_filters.NumberFilter(field_name="stock", lookup_expr="lt")
    stock_gt = django_filters.NumberFilter(field_name="stock", lookup_expr="gt")
    sales_min = django_filters.NumberFilter(method="filter_sales_min")
    sales_max = django_filters.NumberFilter(method="filter_sales_max")
    product_name = django_filters.CharFilter(method="filter_product_name")
    category = django_filters.CharFilter(field_name="product__category", lookup_expr="icontains")
    channel = django_filters.CharFilter(method="filter_channel")

    class Meta:
        model = ProductVariant
        fields = [
            "stock_lt",
            "stock_gt",
            "sales_min",
            "sales_max",
            "product_name",
            "category",
            "channel",
        ]

    def filter_sales_min(self, queryset, name, value):
        return queryset.annotate(
            sales=ExpressionWrapper(
                F("price") * (F("order_count") - F("return_count")),
                output_field=IntegerField()
            )
        ).filter(sales__gte=value)

    def filter_sales_max(self, queryset, name, value):
        return queryset.annotate(
            sales=ExpressionWrapper(
                F("price") * (F("order_count") - F("return_count")),
                output_field=IntegerField()
            )
        ).filter(sales__lte=value)
    
    def filter_product_name(self, queryset, name, value):
            return queryset.filter(product__name__icontains=value)

    def filter_channel(self, queryset, name, value):
        value = (value or "").strip().lower()
        if value in ("online", "offline"):
            # JSONField list containment: channels contains the given value
            return queryset.filter(channels__contains=[value])
        return queryset
    
class InventoryAdjustmentFilter(django_filters.FilterSet):
    variant_code = django_filters.CharFilter(field_name='variant__variant_code', lookup_expr='exact')

    class Meta:
        model = InventoryAdjustment
        fields = ['variant_code']
