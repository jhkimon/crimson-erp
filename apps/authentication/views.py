from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import JSONParser
from apps.authentication.serializers import RegisterSerializer, UserSerializer, PasswordChangeSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import IntegrityError

User = get_user_model()

class SignupView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        operation_summary="회원가입",
        operation_description="새로운 사용자를 등록하고, JWT 토큰을 반환합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password", "first_name", "contact", "role", "status"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 아이디", example="test01"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="test@example.com"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="crimson123"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, example="테스트"),
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
        operation_summary="직원 계정 상태 전환 (STAFF/INTERN/MANAGER)",
        operation_description="MANAGER가 STAFF, INTERN 또는 MANAGER 계정을 승인(APPROVED)하거나 거절(DENIED)할 수 있습니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "status"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="STAFF 사용자 아이디", example="staff1"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, enum=["APPROVED", "DENIED"], description="변경할 상태", example="APPROVED"),
            }
        ),
        responses={
            200: "상태 변경 성공",
            400: "잘못된 요청",
            403: "권한 없음",
            404: "사용자 없음"
        },
        security=[{"BearerAuth": []}],
    )
    def post(self, request):
        if request.user.role != "MANAGER":
            return Response({"error": "STAFF 상태 변경 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get("username")
        input_status = request.data.get("status")

        if not username or not input_status:
            return Response({"error": "username과 status가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 상태 값을 대소문자 무관하게 허용하고 내부적으로 대문자로 통일
        normalized_status = str(input_status).upper()
        if normalized_status not in ["APPROVED", "DENIED"]:
            return Response({"error": "status는 APPROVED 또는 DENIED여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "해당 사용자가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        # STAFF / INTERN / MANAGER 모두 승인 대상 허용
        if user.role not in ["STAFF", "INTERN", "MANAGER"]:
            return Response({"error": "해당 사용자는 승인 대상(STAFF/INTERN/MANAGER)이 아닙니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 상태 전환
        user.status = normalized_status
        user.save()

        return Response({"message": f"{username} 계정이 {normalized_status} 상태로 변경되었습니다."}, status=status.HTTP_200_OK)

# Login API
class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="로그인",
        operation_description="사용자 로그인 후 JWT 토큰과 사용자 정보를 반환합니다. STAFF의 경우 approved 상태여야 로그인 가능합니다.",
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
                    "user": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "username": openapi.Schema(type=openapi.TYPE_STRING),
                            "email": openapi.Schema(type=openapi.TYPE_STRING),
                            "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                            "contact": openapi.Schema(type=openapi.TYPE_STRING),
                            "role": openapi.Schema(type=openapi.TYPE_STRING),
                            "status": openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    ),
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
            # 퇴사/비활성 및 소프트 삭제 계정 로그인 차단
            if not user.is_active:
                return Response({"error": "비활성화된 계정입니다."}, status=status.HTTP_403_FORBIDDEN)

            if getattr(user, "is_deleted", False):
                return Response({"error": "삭제된 계정입니다."}, status=status.HTTP_403_FORBIDDEN)

            if user.role == "STAFF" and user.status.upper() != "APPROVED":
                return Response({"error": "승인되지 않은 STAFF 계정입니다."}, status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data

            return Response(
                {
                    "message": "Login successful",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "user": user_data
                },
                status=status.HTTP_200_OK,
            )

        return Response({"error": "존재하지 않는 계정입니다."}, status=status.HTTP_401_UNAUTHORIZED)

# Logout API
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
        
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="비밀번호 변경 (본인 또는 매니저)",
        operation_description="""
        로그인한 본인의 비밀번호를 직접 변경하거나, 'MANAGER' 권한을 가진 사용자가 다른 직원의 비밀번호를 변경합니다.
        - **일반 사용자:** URL의 employee_id에 자신의 ID를 넣어서 요청해야 합니다.
        - **매니저:** URL의 employee_id에 대상 직원의 ID를 넣어 요청할 수 있습니다.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="새 비밀번호", example="new_strong_password!"),
            },
            required=["password"]
        ),
        responses={
            200: openapi.Response(description="비밀번호가 성공적으로 변경되었습니다."),
            400: "Bad Request - 유효하지 않은 데이터",
            403: "Forbidden - 권한 없음",
            404: "Not Found - 직원을 찾을 수 없음"
        }
    )
    def put(self, request, employee_id):
        # 1. 대상 직원을 찾음
        target_user = get_object_or_404(User, id=employee_id, is_deleted=False)
        
        # 2. 권한 확인: 요청자가 매니저이거나, 대상이 본인인지 확인
        if not (request.user.role == 'MANAGER' or request.user.id == target_user.id):
            return Response(
                {"error": "비밀번호를 변경할 권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 3. Serializer를 통해 데이터 유효성 검사
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            # 4. Django의 set_password를 사용하여 안전하게 비밀번호 설정
            new_password = serializer.validated_data['password']
            target_user.set_password(new_password)
            target_user.save()
            
            return Response({"message": f"사용자 '{target_user.username}'의 비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
