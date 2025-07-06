from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser
from apps.authentication.serializers import RegisterSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
         
User = get_user_model()

from django.db import IntegrityError

class SignupView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        operation_summary="회원가입",
        operation_description="새로운 사용자를 등록하고, JWT 토큰을 반환합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password", "full_name", "contact", "role", "status"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 아이디", example="test01"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="test@example.com"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="crimson123"),
                "full_name": openapi.Schema(type=openapi.TYPE_STRING, example="테스트"),
                "contact": openapi.Schema(type=openapi.TYPE_STRING, example="010-1234-5678"),
            }
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING, description="성공 메시지"),
                    "access_token": openapi.Schema(type=openapi.TYPE_STRING, description="JWT 액세스 토큰"),
                    "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="JWT 리프레시 토큰"),
                },
            ),
            400: "잘못된 입력",
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "message": "Signup successful",
                        "access_token": str(refresh.access_token),
                        "refresh_token": str(refresh),
                    },
                    status=status.HTTP_201_CREATED,
                )
            except IntegrityError as e:
                return Response(
                    {"error": "이미 사용 중인 사용자 이름(username) 또는 이메일입니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ApproveStaffView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="STAFF 계정 상태 전환",
        operation_description="MANAGER가 STAFF 계정을 승인하거나 비활성화할 수 있습니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "status"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="STAFF 사용자 아이디", example="staff1"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, enum=["approved", "denied"], description="변경할 상태", example="denied"),
            }
        ),
        responses={
            200: "상태 변경 성공",
            400: "잘못된 요청",
            403: "권한 없음",
            404: "STAFF 없음"
        },
        security=[{"BearerAuth": []}],
    )
    def post(self, request):
        if request.user.role != "MANAGER":
            return Response({"error": "STAFF 상태 변경 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get("username")
        new_status = request.data.get("status")

        if not username or new_status not in ["approved", "denied"]:
            return Response({"error": "username과 유효한 status(approved/denied)가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "해당 사용자가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        if user.role != "STAFF":
            return Response({"error": "해당 사용자는 STAFF가 아닙니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 상태 전환
        user.status = new_status
        user.save()

        return Response({"message": f"{username} 계정이 {new_status} 상태로 변경되었습니다."}, status=status.HTTP_200_OK)

# Login API
class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="로그인",
        operation_description="사용자 로그인 후 JWT 토큰을 반환합니다. STAFF의 경우 active 상태여야 로그인 가능합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 아이디", example="staff1"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="비밀번호", example="crimson123"),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "access_token": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            401: "잘못된 로그인 정보",
            403: "승인되지 않은 계정"
        },
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            if user.role == "STAFF" and user.status != "approved":
                return Response({"error": "승인되지 않은 STAFF 계정입니다."}, status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "message": "Login successful",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                },
                status=status.HTTP_200_OK,
            )
        return Response({"error": "존재하지 않는 계정입니다."}, status=status.HTTP_401_UNAUTHORIZED)



# 🔹 Logout API
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="로그아웃",
        operation_description="리프레시 토큰을 블랙리스트에 등록하여 로그아웃을 수행합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh_token"],
            properties={
                "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="JWT 리프레시 토큰"),
            },
        ),
        responses={
            200: "로그아웃 성공",
            400: "잘못된 토큰",
        },
        security=[{"BearerAuth": []}],
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # ✅ Refresh Token 블랙리스트 처리
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)