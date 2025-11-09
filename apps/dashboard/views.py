# apps/dashboard/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from .serializers import DashboardNotificationSerializer

class HRNotificationView(APIView):
    permission_classes = [IsAuthenticated]

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
