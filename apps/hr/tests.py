from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import date, timedelta
from apps.hr.models import Employee, VacationRequest

class EmployeeVacationAPITestCase(APITestCase):
    def setUp(self):
        self.employee = Employee.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            first_name="김정현",
            role="STAFF",
            is_active=True
        )
        self.client.force_authenticate(user=self.employee)
        self.client.login(username="testuser", password="testpass123")

    def test_employee_list(self):
        """GET /api/v1/hr/employees/ - 직원 목록 조회"""
        url = "/api/v1/hr/employees/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['username'], self.employee.username)

    def test_employee_detail_view(self):
        """GET /api/v1/hr/employees/{id}/ - 직원 상세 조회"""
        url = f"/api/v1/hr/employees/{self.employee.id}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["email"], self.employee.email)

    def test_employee_update(self):
        """PATCH /api/v1/hr/employees/{id}/ - 직원 정보 수정"""
        url = f"/api/v1/hr/employees/{self.employee.id}/"
        payload = {
            "contact": "010-9999-9999",
            "annual_leave_days": 30
        }
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.contact, "010-9999-9999")
        self.assertEqual(self.employee.annual_leave_days, 30)

    def test_employee_detail_includes_vacation_days(self):
        """GET /api/v1/hr/employees/{id}/ - 직원 상세 조회 시 vacation_days, vacation_pending_days 필드 확인"""
        # 휴가 2개 생성: 1개는 APPROVED, 1개는 PENDING
        VacationRequest.objects.create(
            employee=self.employee,
            leave_type="VACATION",
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 2),
            status="APPROVED"
        )
        VacationRequest.objects.create(
            employee=self.employee,
            leave_type="SICK",
            start_date=date(2025, 8, 10),
            end_date=date(2025, 8, 10),
            status="PENDING"
        )

        url = f"/api/v1/hr/employees/{self.employee.id}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # 필드 존재 여부 확인
        self.assertIn("vacation_days", r.data)
        self.assertIn("vacation_pending_days", r.data)

        # APPROVED 휴가 1건 확인
        vacation_days = r.data["vacation_days"]
        self.assertEqual(len(vacation_days), 1)
        self.assertEqual(str(vacation_days[0]["start_date"]), "2025-08-01")
        self.assertEqual(str(vacation_days[0]["end_date"]), "2025-08-02")
        self.assertEqual(vacation_days[0]["leave_type"], "VACATION")

        # PENDING 휴가 1건 확인
        pending_days = r.data["vacation_pending_days"]
        self.assertEqual(len(pending_days), 1)
        self.assertEqual(str(pending_days[0]["start_date"]), "2025-08-10")
        self.assertEqual(str(pending_days[0]["end_date"]), "2025-08-10")
        self.assertEqual(pending_days[0]["leave_type"], "SICK")

    def test_vacation_create(self):
        """POST /api/v1/hr/vacations/ - 휴가 신청"""
        url = "/api/v1/hr/vacations/"
        today = date.today()
        payload = {
            "employee": self.employee.id,
            "leave_type": "VACATION",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "reason": "개인 사유"
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VacationRequest.objects.count(), 1)
        self.assertEqual(r.data["leave_type"], "VACATION")

    def test_half_day_validation(self):
        """POST /api/v1/hr/vacations/ - 반차 날짜 검증"""
        url = "/api/v1/hr/vacations/"
        today = date.today()
        payload = {
            "employee": self.employee.id,
            "leave_type": "HALF_DAY_AM",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("반차는 시작일과 종료일이 같아야 합니다.", str(r.data))

    def test_vacation_status_update(self):
        """PATCH /api/v1/hr/vacations/review/{id}/ - 휴가 상태 변경"""
        vacation = VacationRequest.objects.create(
            employee=self.employee,
            leave_type="VACATION",
            start_date=date.today(),
            end_date=date.today(),
            reason="테스트",
            status="PENDING"
        )
        self.employee.role = "MANAGER"
        self.employee.save()
        url = f"/api/v1/hr/vacations/review/{vacation.id}/"
        payload = {"status": "APPROVED"}
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        vacation.refresh_from_db()
        self.assertEqual(vacation.status, "APPROVED")