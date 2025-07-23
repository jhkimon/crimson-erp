from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from apps.hr.models import Employee

class EmployeeAPITestCase(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_superuser=True,
            is_staff=True
        )
        refresh = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.employee = Employee.objects.create_user(
            username="employee1",
            email="e1@example.com",
            password="pass1234",
            role="manager",
            contact="010-1234-5678",
            status="active"
        )

        self.base_url = "/api/v1/hr/employees/"
        self.detail_url = f"{self.base_url}{self.employee.id}/"

    def test_get_employee_list(self):
        res = self.client.get(self.base_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usernames = [emp["username"] for emp in res.data]
        self.assertIn("employee1", usernames)

    def test_create_employee(self):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "role": "STAFF",
            "contact": "010-9999-9999",
            "is_superuser": False,
            "is_staff": False
        }
        res = self.client.post(self.base_url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Employee.objects.filter(username="newuser").exists())

    def test_get_employee_detail(self):
        res = self.client.get(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], self.employee.username)

    def test_update_employee(self):
        update_data = {
            "email": "updated@example.com",
            "role": "MANAGER",
            "contact": "010-0000-0000",
            "status": "active",
            "is_superuser": False,
            "is_staff": False,
            "is_active": True
        }
        res = self.client.put(self.detail_url, update_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.email, "updated@example.com")

    def test_deactivate_employee(self):
        res = self.client.patch(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertEqual(self.employee.status, "inactive")