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

class EmployeeCreateSerializer(serializers.ModelSerializer):
    """직원 생성용 Serializer"""
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Employee
        fields = (
            'id', 'username', 'email', 'password', 'role', 'contact',
            'is_superuser', 'is_staff'
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': True},
            'email': {'required': True},
            'is_superuser': {'required': False},
            'is_staff': {'required': False}
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        # AbstractUser는 set_password 메서드를 제공함
        employee = Employee.objects.create_user(
            **validated_data,
            status='active'
        )
        employee.set_password(password)
        employee.save()
        return employee

class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """직원 정보 수정용 Serializer"""
    class Meta:
        model = Employee
        fields = (
            'email', 'role', 'contact', 'status',
            'is_superuser', 'is_staff', 'is_active'
        )
        extra_kwargs = {
            'email': {'required': False},
            'role': {'required': False},
            'contact': {'required': False},
            'status': {'required': False},
            'is_superuser': {'required': False},
            'is_staff': {'required': False},
            'is_active': {'required': False}
        }

class EmployeeDeactivateSerializer(serializers.ModelSerializer):
    """직원 비활성화용 Serializer"""
    class Meta:
        model = Employee
        fields = ('id', 'username', 'status', 'is_active')
        read_only_fields = ('id', 'username', 'status', 'is_active')
