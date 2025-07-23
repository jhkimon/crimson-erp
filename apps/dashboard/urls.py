from django.urls import path
from .views import DashboardSummaryView

urlpatterns = [
    path("", DashboardSummaryView.as_view(), name="dashboard-view"),  # 직원 목록 조회(GET), 직원 등록(POST)
]
