from rest_framework import serializers
from .models import Employee

class EmployeeListSerializer(serializers.ModelSerializer):
    """직원 목록 조회용 Serializer"""
    class Meta:
        model = Employee
        fields = (
            'id', 'username', 'email', 'role', 'contact', 'status',
            'is_active', 'is_superuser', 'is_staff', 'date_joined'
        )
        read_only_fields = ('id', 'date_joined')

class EmployeeDetailSerializer(serializers.ModelSerializer):
    """직원 상세 정보 조회용 Serializer"""
    class Meta:
        model = Employee
        fields = (
            'id', 'username', 'email', 'role', 'contact', 'status',
            'is_active', 'is_superuser', 'is_staff', 'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'date_joined', 'last_login')

class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """직원 정보 수정용 Serializer (HR용)"""
    class Meta:
        model = Employee
        fields = (
            'email', 'role', 'contact', 'is_active'
        )
        extra_kwargs = {
            'email': {'required': False},
            'role': {'required': False},
            'contact': {'required': False},
            'is_active': {'required': False}, # 퇴사 여부
        }