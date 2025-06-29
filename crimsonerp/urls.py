from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny

schema_view = get_schema_view(
    openapi.Info(
        title="CrimsonERP API",
        default_version="v1",
        description="CrimsonERP API with JWT Authentication",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="nextku.contact@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

schema_view = get_schema_view(
    openapi.Info(
        title="CrimsonERP API",
        default_version="v1",
        description="CrimsonERP API with JWT Authentication",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="nextku.contact@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

# 기본 홈 페이지 응답
def home(request):
    return JsonResponse({"message": "API에 오신 것을 환영합니다! /swagger나 /redoc을 확인해주세요"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # 기본 홈 페이지
    path("api/v1/", include("api.v1.urls")),  # API v1 등록

    # Swagger UI (API 테스트 가능)
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),

    # ReDoc (문서 전용, 테스트 불가)
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]