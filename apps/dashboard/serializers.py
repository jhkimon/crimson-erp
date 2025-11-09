# apps/dashboard/serializers.py
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
        self._check_permission()
        return VacationRequest.objects.filter(status='PENDING').count()

    def get_pending_order_count(self, obj):
        self._check_permission()
        return Order.objects.filter(status='PENDING').count()
