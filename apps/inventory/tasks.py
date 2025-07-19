from django.test import TestCase
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import StockReservation
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_reservations():
    """
    만료된 재고 예약을 자동으로 정리하는 배치 작업
    주기적으로 실행 (예: 5분마다)
    """
    try:
        with transaction.atomic():
            expired_reservations = StockReservation.objects.filter(
                expires_at__lt=timezone.now(),
                is_confirmed=False
            ).select_related('variant', 'transaction_item__transaction')

            cleaned_count = 0
            for reservation in expired_reservations:
                # 예약 재고 해제
                variant = reservation.variant
                variant.reserved_stock = max(0,
                                             variant.reserved_stock - reservation.reserved_quantity
                                             )
                variant.save()

                # 관련 주문을 취소 상태로 변경
                transaction_obj = reservation.transaction_item.transaction
                if transaction_obj.status == 'pending':
                    transaction_obj.status = 'cancelled'
                    transaction_obj.save()

                reservation.delete()
                cleaned_count += 1

            logger.info(f"만료된 예약 {cleaned_count}개 정리 완료")
            return cleaned_count

    except Exception as e:
        logger.error(f"예약 정리 중 오류: {str(e)}")
        raise


@shared_task
def sync_pos_inventory(channel_id):
    """
    특정 채널의 POS 시스템과 재고 동기화
    """
    # POS API를 통해 재고 정보를 가져와서 동기화하는 로직
    pass
