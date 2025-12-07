# apps/dashboard/urls.py
from django.urls import path
from .views import DashboardNotificationView

urlpatterns = [
    path('notifications/', DashboardNotificationView.as_view(), name='hr-notifications'),
]
