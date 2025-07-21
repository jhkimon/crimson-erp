from django.core.mail import send_mail

def format_order_items(order):
    lines = []
    for item in order.items.all():
        lines.append(
            f"- {item.variant.product.name} ({item.spec or ''}) | {item.quantity}개 × {item.unit_price:,}원 = {item.total_price:,}원"
        )
    return "\n".join(lines)

def send_order_approved_email(order):
    subject = f"[CrimsonERP] 주문 #{order.id} 승인 완료"
    message = (
        f"[주문 승인 안내]\n\n"
        f"발주 번호: {order.id}\n"
        f"공급처: {order.supplier.name}\n"
        f"담당자: {order.manager.first_name if order.manager else '-'}\n"
        f"주문 상태: {order.status}\n"
        f"발주일: {order.order_date}\n"
        f"예상 납기일: {order.expected_delivery_date}\n\n"
        f"[주문 품목]\n"
        f"{format_order_items(order)}\n\n"
        f"해당 주문이 승인되었습니다. 납품을 준비해주세요."
    )
    send_mail(subject, message, 'admin@crimsonerp.com', ['nextku.contact@gmail.com'])

def send_order_created_email(order):
    subject = f"[CrimsonERP] 주문 #{order.id} 생성 완료"
    message = (
        f"[발주 요청 생성 안내]\n\n"
        f"발주 번호: {order.id}\n"
        f"공급처: {order.supplier.name}\n"
        f"담당자: {order.manager.first_name if order.manager else '-'}\n"
        f"주문 상태: {order.status}\n"
        f"발주일: {order.order_date}\n"
        f"예상 납기일: {order.expected_delivery_date}\n\n"
        f"[주문 품목]\n"
        f"{format_order_items(order)}\n\n"
        f"해당 발주가 생성되었습니다. 승인 여부를 확인해주세요."
    )
    send_mail(subject, message, 'admin@crimsonerp.com', ['nextku.contact@gmail.com'])