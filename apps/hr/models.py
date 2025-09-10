from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password

class Employee(AbstractUser):
    ROLE_CHOICES = [
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff'),
        ('INTERN', 'Intern')
    ]

    STATUS_CHOICES = [
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
    ]

    ALLOWED_TABS = [
        ('SUPPLIER', 'Supplier'),
        ('ORDER', 'Order'),
        ('INVENTORY', 'Inventory'),
        ('HR', 'hr')
    ]

    GENDER_CHOICES = [
        ('MALE', '남성'),
        ('FEMALE', '여성'),
    ]

    def default_allowed_tabs():
        return ['INVENTORY']


    # AbstractUser에서 이미 제공하는 필드들:
    # id, username, password, email, is_superuser, is_staff, is_active, last_login, date_joined
    
    # 추가 필드만 정의
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF')
    contact = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DENIED')
    hire_date = models.DateField(null=True, blank=True)
    annual_leave_days = models.PositiveIntegerField(default=24)
    allowed_tabs = models.JSONField(default=default_allowed_tabs, blank=True, help_text="사용자별 접근 허용 탭 목록")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    @property
    def remaining_leave_days(self):
        used_days = 0

        for req in self.vacation_requests.filter(status='APPROVED'):
            if req.leave_type == 'VACATION':
                used_days += (req.end_date - req.start_date).days + 1
            elif req.leave_type in ['HALF_DAY_AM', 'HALF_DAY_PM']:
                used_days += 0.5
            # SICK, OTHER는 연차 차감 없음

        return self.annual_leave_days - used_days
    class Meta:
        db_table = 'auth_user'  # 테이블명을 auth_user로 설정

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
class VacationRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('VACATION', '연차'),
        ('HALF_DAY_AM', '오전 반차'),
        ('HALF_DAY_PM', '오후 반차'),
        ('SICK', '병가'),
        ('OTHER', '기타'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '대기중'),
        ('APPROVED', '승인됨'),
        ('REJECTED', '거절됨'),
        ('CANCELLED', '취소됨'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="vacation_requests")
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.full_name} - {self.start_date}~{self.end_date} [{self.get_leave_type_display()} | {self.get_status_display()}]"