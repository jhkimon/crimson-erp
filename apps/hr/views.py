from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Employee, VacationRequest
from .serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeUpdateSerializer,
    VacationRequestSerializer, 
    VacationRequestCreateSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

def can_approve_or_reject(user):
    return user.role == "MANAGER"

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)

class EmployeeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="직원 목록 조회",
        responses={
            200: EmployeeListSerializer(many=True)
        }
    )
    def get(self, request):
        """직원 목록 조회"""
        employees = Employee.objects.filter(is_deleted=False)
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class EmployeeDetailUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="특정 직원 조회",
        responses={
            200: EmployeeDetailSerializer(),
            404: "Not Found"
        }
    )
    def get(self, request, employee_id):
        """특정 직원 조회"""
        employee = get_object_or_404(Employee, id=employee_id, is_deleted=False)
        serializer = EmployeeDetailSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="직원 정보 수정 (HR 전용)",
        operation_description="직원의 이름, 이메일, 연락처, 퇴사 여부, 연차일수, 권한 탭, 입사일, 직무, 삭제 여부를 수정합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="직원 이메일", example="john.doe@example.com"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, description="이름", example="유시진"),
                "contact": openapi.Schema(type=openapi.TYPE_STRING, description="직원 연락처", example="010-1234-5678"),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="퇴사 여부 (false이면 퇴사)", example=True),
                "annual_leave_days": openapi.Schema(type=openapi.TYPE_INTEGER, description="연차일수", example=24),
                "allowed_tabs": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="접근 허용 탭 목록 (예: ['INVENTORY', 'HR'])",
                    example=["INVENTORY", "SUPPLIER", "ORDER", "HR"]
                ),
                "hire_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="입사일", example="2024-03-01"),
                "role": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="직무 구분",
                    enum=["MANAGER", "STAFF", "INTERN"],
                    example="STAFF"
                ),
                "is_deleted": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="삭제 여부(소프트 삭제)",
                    example=False
                ),
                "gender": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="성별",
                    enum=["MALE", "FEMALE"],
                    example="MALE"
                )
            },
            required=[],
        ),
        responses={
            200: EmployeeDetailSerializer(),
            400: "Bad Request",
            404: "Not Found"
        }
    )
    def patch(self, request, employee_id):
        employee = get_object_or_404(Employee, id=employee_id)
        serializer = EmployeeUpdateSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = EmployeeDetailSerializer(employee)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VacationRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="휴가 신청 목록 조회",
        responses={200: VacationRequestSerializer(many=True)}
    )
    def get(self, request):
        """휴가 신청 전체 조회"""
        requests = VacationRequest.objects.select_related('employee').all()
        serializer = VacationRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="휴가 신청 등록",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["employee", "leave_type", "start_date", "end_date"],
            properties={
                "employee": openapi.Schema(type=openapi.TYPE_INTEGER, description="직원 ID", example=168),
                "leave_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="휴가 유형",
                    enum=["VACATION", "HALF_DAY_AM", "HALF_DAY_PM", "SICK", "OTHER"],
                    example="VACATION"
                ),
                "start_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", example="2025-08-01"),
                "end_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", example="2025-08-02"),
                "reason": openapi.Schema(type=openapi.TYPE_STRING, description="사유", example="개인 사정으로 인한 연차")
            }
        ),
        responses={
            201: VacationRequestSerializer(),
            400: "Bad Request"
        }
    )
    def post(self, request):
        """휴가 신청 등록"""
        serializer = VacationRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            leave_type = data.get("leave_type")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            if leave_type in ["HALF_DAY_AM", "HALF_DAY_PM"] and start_date != end_date:
                return Response(
                    {"error": "반차는 시작일과 종료일이 같아야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if leave_type == "VACATION" and start_date > end_date:
                return Response(
                    {"error": "종료일은 시작일보다 빠를 수 없습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            request_instance = serializer.save()
            response_serializer = VacationRequestSerializer(request_instance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class VacationRequestReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="휴가 신청 취소/승인/거절",
        operation_description="휴가 신청 상태를 승인(APPROVED), 거절(REJECTED), 대기중(PENDING), 취소(CANCELLED) 중 하나로 변경합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["APPROVED", "REJECTED"],
                    description="변경할 상태값",
                    example="APPROVED"
                )
            },
            required=["status"]
        ),
        responses={
            200: VacationRequestSerializer(),
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found"
        }
    )
    def patch(self, request, pk):
        """휴가 신청 승인/거절"""
        vacation = get_object_or_404(VacationRequest, pk=pk)
        new_status = request.data.get("status")

        if new_status not in ["APPROVED", "REJECTED", "PENDING", "CANCELLED"]:
            return Response({"error": "Invalid status value."}, status=status.HTTP_400_BAD_REQUEST)

        if vacation.status == new_status:
            return Response({"error": f"이미 상태가 '{new_status}'입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not can_approve_or_reject(request.user) and new_status in ["APPROVED", "REJECTED"]:
            return Response({"error": "권한이 없습니다. 관리자만 승인 또는 거절할 수 있습니다."},
                            status=status.HTTP_403_FORBIDDEN)

        # 상태 업데이트 및 기록 시간
        vacation.status = new_status
        vacation.reviewed_at = timezone.now()
        vacation.save()

        serializer = VacationRequestSerializer(vacation)
        return Response(serializer.data, status=status.HTTP_200_OK)