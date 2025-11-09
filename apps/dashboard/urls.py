# apps/dashboard/urls.py
from django.urls import path
from .views import HRNotificationView

urlpatterns = [
    path('notifications/', HRNotificationView.as_view(), name='hr-notifications'),
]
