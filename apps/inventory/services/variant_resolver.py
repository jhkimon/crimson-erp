from apps.inventory.models import ProductVariant

def resolve_variant(product, option, detail_option, variant_code):
    """
    - 기존 Variant 있으면 반환
    - 없으면 None
    """

    if variant_code:
        existing = ProductVariant.objects.filter(
            variant_code=variant_code
        ).first()
        if existing:
            return existing

    if option:
        return ProductVariant.objects.filter(
            product=product,
            option=option,
            detail_option=detail_option,
        ).first()

    return ProductVariant.objects.filter(
        product=product,
        option="",
    ).first()
