from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser

# Serializer
from apps.authentication.serializers import RegisterSerializer
# 문서화
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
         
User = get_user_model()
# 🔹 Signup API
class SignupView(APIView):
    permission_classes = [AllowAny]  # 누구나 접근 가능
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        operation_summary="회원가입",
        operation_description="새로운 사용자를 등록하고, JWT 토큰을 반환합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 아이디 (유니크)"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="이메일"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="비밀번호"),
            },
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
            User = serializer.save()    
            refresh = RefreshToken.for_user(User)  # ✅ JWT만 발급 (Token 제거)
            return Response(
                {
                    "message": "Signup successful",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 🔹 Login API
class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="로그인",
        operation_description="사용자 로그인 후 JWT 토큰을 반환합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 아이디"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="비밀번호"),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING, description="성공 메시지"),
                    "access_token": openapi.Schema(type=openapi.TYPE_STRING, description="JWT 액세스 토큰"),
                    "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="JWT 리프레시 토큰"),
                },
            ),
            401: "잘못된 로그인 정보",
        },
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)  # ✅ JWT만 발급 (Token 제거)
            return Response(
                {
                    "message": "Login successful",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                },
                status=status.HTTP_200_OK,
            )
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


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