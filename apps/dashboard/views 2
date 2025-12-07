from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import DashboardNotificationSerializer

class DashboardNotificationView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_summary="대시보드 알림 조회",
        operation_description="""
        로그인된 사용자의 HR 및 발주 관련 승인대기 알림을 조회합니다.
        **Manager (관리자) 에게만 뜨는 알림이며, 이외의 경우 401/403 ERROR 발생**
        """,
        tags=["Dashboard"]
    )

    def get(self, request):
        serializer = DashboardNotificationSerializer({}, context={'request': request})
        try:
            data = serializer.data
            return Response(data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                "success": False,
                "message": "알 수 없는 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
