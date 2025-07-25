from django.urls import path, include

urlpatterns = [
    path("dashboard/", include("apps.dashboard.urls")), # 대시보드 API 라우트
    path("hr/", include("apps.hr.urls")),  # HR 앱의 API 라우트
    path("inventory/", include("apps.inventory.urls")),  # Inventory 앱의 API 라우트
    path("authentication/", include("apps.authentication.urls")),  # 인증 API 라우트
    path("orders/", include("apps.orders.urls")),  # 주문 API 라우트
    path("supplier/", include("apps.supplier.urls")) # 공급업체 API 라우트
]