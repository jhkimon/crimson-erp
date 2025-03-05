from django.urls import path
from .views import SignupView, LoginView, LogoutView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="authentication_signup_create"),
    path("login/", LoginView.as_view(), name="authentication_login"),
    path("logout/", LogoutView.as_view(), name="authentication_logout"),
]