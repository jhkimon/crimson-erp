import re

def slug(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    return s.upper() or "DEFAULT"

def generate_variant_code(product_id: str, option: str = "", detail_option: str = "") -> str:
    opt = slug(option)           # "" -> DEFAULT
    det = slug(detail_option) if detail_option else ""  # "" 유지

    return f"{product_id}-{opt}" if not det else f"{product_id}-{opt}-{det}"
