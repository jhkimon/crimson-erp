from django.urls import path
from .views import SignupView, LoginView, LogoutView, ApproveStaffView, PasswordChangeView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="authentication_signup_create"),
    path("login/", LoginView.as_view(), name="authentication_login"),
    path("logout/", LogoutView.as_view(), name="authentication_logout"),
    path("approve/", ApproveStaffView.as_view(), name="approve_staff"), 
    path("change-password/<int:employee_id>/", PasswordChangeView.as_view(), name="auth_change_password"),
]