from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from apps.orders.models import Order
from apps.hr.models import VacationRequest

class DashboardNotificationSerializer(serializers.Serializer):
    """대시보드 알림 Serializer — 관리자만 접근 가능"""
    pending_vacation_count = serializers.SerializerMethodField()
    pending_order_count = serializers.SerializerMethodField()

    def _check_permission(self):
        user = self.context.get('request').user
        if not user or not user.is_authenticated:
            raise PermissionDenied("로그인된 사용자만 접근할 수 있습니다.")
        if user.role.upper() != 'MANAGER':
            raise PermissionDenied("관리자만 접근 가능합니다.")
        return user

    def get_pending_vacation_count(self, obj):
        """오늘 이후 시작 & 탈퇴하지 않은 직원의 대기중 휴가"""
        self._check_permission()
        today = timezone.now().date()
        return VacationRequest.objects.filter(
            employee__is_deleted=False,
            status='PENDING',
            start_date__gte=today
        ).count()

    def get_pending_order_count(self, obj):
        """오늘 이후 납기 & 탈퇴하지 않은 직원(매니저)의 대기중 주문"""
        self._check_permission()
        today = timezone.now().date()
        return Order.objects.filter(
            manager__is_deleted=False,
            status='PENDING',
            expected_delivery_date__gte=today
        ).count()
