from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password

class Employee(AbstractUser):
    ROLE_CHOICES = [
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff'),
    ]

    STATUS_CHOICES = [
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
    ]

    # AbstractUser에서 이미 제공하는 필드들:
    # id, username, password, email, is_superuser, is_staff, is_active, last_login, date_joined
    
    # 추가 필드만 정의
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF')
    full_name = models.CharField(max_length=50, default="이름없음")
    contact = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='denied')

    class Meta:
        db_table = 'auth_user'  # 테이블명을 auth_user로 설정

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
