from rest_framework import serializers
from .models import Employee, VacationRequest

class EmployeeListSerializer(serializers.ModelSerializer):
    """직원 목록 조회용 Serializer"""
    class Meta:
        model = Employee
        fields = (
            'id', 'username', 'email', 'role', 'contact', 'status',
            'first_name', 'is_active', 'hire_date', 'remaining_leave_days', 'gender'
        )
        read_only_fields = ('id', 'hire_date')

class EmployeeDetailSerializer(serializers.ModelSerializer):
    remaining_leave_days = serializers.SerializerMethodField()
    allowed_tabs = serializers.JSONField()
    vacation_days = serializers.SerializerMethodField()
    vacation_pending_days = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            'id', 'username', 'email', 'role', 'contact', 'status',
            'first_name', 'is_active', 'hire_date',
            'annual_leave_days', 'allowed_tabs', 'remaining_leave_days',
            'vacation_days', 'vacation_pending_days', 'gender'
        )

    def get_remaining_leave_days(self, obj):
        return obj.remaining_leave_days

    def get_vacation_days(self, obj):
        return self._get_vacation_periods(obj, status='APPROVED')

    def get_vacation_pending_days(self, obj):
        return self._get_vacation_periods(obj, status='PENDING')

    def _get_vacation_periods(self, obj, status):
        result = []
        qs = obj.vacation_requests.filter(status=status)
        for req in qs:
            result.append({
                "start_date": req.start_date,
                "end_date": req.end_date,
                "leave_type": req.leave_type
            })
        return result

class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """직원 정보 수정용 Serializer (HR용)"""
    class Meta:
        model = Employee
        fields = (
            'email', 'contact', 'is_active', 'first_name',
            'annual_leave_days', 'allowed_tabs', 'hire_date', 'role', 'gender', 'is_deleted'
        )
        extra_kwargs = {
            'email': {'required': False},
            'contact': {'required': False},
            'is_active': {'required': False},
            'first_name': {'required': False},
            'annual_leave_days': {'required': False},
            'allowed_tabs': {'required': False},
            'hire_date': {'required': False},
            'role': {'required': False},
            'gender': {'required': False},
            'is_deleted': {'required': False},
        }

class VacationRequestSerializer(serializers.ModelSerializer):
    """휴가 신청 조회용 Serializer"""
    employee_name = serializers.CharField(source='employee.first_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = VacationRequest
        fields = [
            'id', 'employee', 'employee_name', 'start_date', 'end_date', 'leave_type',
            'reason', 'status', 'status_display', 'created_at', 'reviewed_at'
        ]
        read_only_fields = ['id', 'employee_name', 'leave_type', 'status_display', 'created_at', 'reviewed_at']

class VacationRequestCreateSerializer(serializers.ModelSerializer):
    """휴가 신청 생성용 Serializer"""
    
    class Meta:
        model = VacationRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason']

    