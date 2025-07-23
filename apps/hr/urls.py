from django.urls import path
from .views import (
    EmployeeListCreateView,  # 직원 목록 조회(GET) + 직원 등록(POST)
    EmployeeDetailUpdateView,  # 특정 직원 조회(GET), 직원 정보 수정(PUT), 직원 비활성화(PATCH)
    VacationRequestView, # 휴가 신청
    VacationRequestReviewView # 휴가 승인 / 반려
)

urlpatterns = [
    path("employees/", EmployeeListCreateView.as_view(), name="employee-list-create"),  # 직원 목록 조회(GET), 직원 등록(POST)
    path("employees/<int:employee_id>/", EmployeeDetailUpdateView.as_view(), name="employee-detail-update"),  # 특정 직원 조회(GET), 직원 정보 수정(PUT), 직원 비활성화(PATCH)
    path("vacation/", VacationRequestView.as_view()),
    path("vacation/<int:pk>/", VacationRequestReviewView.as_view()),
]
