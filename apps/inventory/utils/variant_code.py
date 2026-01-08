import re
import hashlib


def normalize(val: str) -> str:
    return (val or "").strip().lower()


def slug(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    return s.upper() or "DEFAULT"


def generate_internal_variant_code(product_key: str, option: str, product_name: str):
    """
    product_id가 없을 때 사용하는 내부 SKU
    항상 같은 입력 → 같은 코드
    """
    base = f"{product_key}|{normalize(option)}|{normalize(product_name)}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    return f"{product_key}-AUTO-{digest}"


def build_variant_code(
    *,
    product_id: str | None,
    product_name: str,
    option: str = "",
    detail_option: str = "",
    allow_auto: bool = False,
) -> str:
    """
    variant_code 생성의 단일 진입점

    - product_id 있으면 → 정식 SKU
    - product_id 없고 allow_auto=True → 내부 AUTO SKU
    """

    if product_id:
        opt = slug(option)
        det = slug(detail_option) if detail_option else ""
        return f"{product_id}-{opt}" if not det else f"{product_id}-{opt}-{det}"

    if not allow_auto:
        raise ValueError("product_id is required to generate variant_code")

    # product_id 없을 때 fallback key (상품명 앞 3글자)
    product_key = normalize(product_name)[:3] or "PRD"
    return generate_internal_variant_code(product_key, option, product_name)
