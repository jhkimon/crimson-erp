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
    permission_classes = [AllowAny]

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
        # 관리자 권한(ROLE: MANAGER) 체크
        if getattr(request.user, "role", None) != "MANAGER":
            return Response({"error": "권한이 없습니다. 관리자만 수정할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

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
        operation_description="휴가 신청 및 근무 배정 목록을 조회합니다. 쿼리 파라미터로 필터링 가능합니다.",
        manual_parameters=[
            openapi.Parameter('leave_type', openapi.IN_QUERY, description="휴가 유형 필터 (예: VACATION, WORK)", type=openapi.TYPE_STRING),
            openapi.Parameter('employee', openapi.IN_QUERY, description="직원 ID 필터", type=openapi.TYPE_INTEGER),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="시작일 필터 (YYYY-MM-DD)", type=openapi.TYPE_STRING, format="date"),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="종료일 필터 (YYYY-MM-DD)", type=openapi.TYPE_STRING, format="date"),
        ],
        responses={200: VacationRequestSerializer(many=True)}
    )
    def get(self, request):
        """휴가 신청 전체 조회 (필터링 지원)"""
        queryset = VacationRequest.objects.select_related('employee').all()
        
        # 쿼리 파라미터 필터링
        leave_type = request.query_params.get('leave_type')
        employee_id = request.query_params.get('employee')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if leave_type:
            queryset = queryset.filter(leave_type=leave_type)
        
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        serializer = VacationRequestSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="휴가 신청 등록",
        operation_description="휴가 신청을 등록합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["employee", "leave_type", "start_date", "end_date"],
            properties={
                "employee": openapi.Schema(type=openapi.TYPE_INTEGER, description="직원 ID", example=168),
                "leave_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="휴가 유형 (WORK는 관리자만 생성 가능)",
                    enum=["VACATION", "HALF_DAY_AM", "HALF_DAY_PM", "SICK", "OTHER", "WORK"],
                    example="VACATION"
                ),
                "start_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", example="2025-08-01"),
                "end_date": openapi.Schema(type=openapi.TYPE_STRING, format="date", example="2025-08-02"),
                "reason": openapi.Schema(type=openapi.TYPE_STRING, description="사유", example="개인 사정으로 인한 연차")
            }
        ),
        responses={
            201: VacationRequestSerializer(),
            400: "Bad Request",
            403: "Forbidden"
        }
    )
    def post(self, request):
        """휴가 신청 등록"""
        serializer = VacationRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            leave_type = data.get("leave_type")
            employee = data.get("employee")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            # # WORK 타입은 관리자만 생성 가능
            # if leave_type == "WORK" and getattr(request.user, "role", None) != "MANAGER":
            #     return Response(
            #         {"error": "근무 배정은 관리자만 생성할 수 있습니다."},
            #         status=status.HTTP_403_FORBIDDEN
            #     )

            # 중복 일정 검사 (WORK와 APPROVED된 다른 휴가가 겹치는지 확인)
            if leave_type == "WORK":
                overlapping_requests = VacationRequest.objects.filter(
                    employee=employee,
                    status='APPROVED',
                    start_date__lte=end_date,
                    end_date__gte=start_date
                ).exclude(leave_type='WORK')
                
                if overlapping_requests.exists():
                    return Response(
                        {"error": "해당 기간에 이미 승인된 휴가가 있어 근무 배정할 수 없습니다."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 기존 검증 로직은 serializer의 validate 메서드로 이동됨
            # WORK 타입이면 자동 승인
            if leave_type == "WORK":
                request_instance = serializer.save(status='APPROVED', reviewed_at=timezone.now())
            else:
                request_instance = serializer.save()
            
            response_serializer = VacationRequestSerializer(request_instance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class VacationRequestReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="휴가 신청 취소/승인/거절",
        operation_description="휴가 신청 상태를 승인(APPROVED), 거절(REJECTED), 대기중(PENDING), 취소(CANCELLED) 중 하나로 변경합니다. WORK 타입은 생성 시 자동 승인되므로 일반적으로 이 API를 사용할 필요가 없습니다.",
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
        
        # 근무가 겹치면 근무 삭제
        if new_status == "APPROVED":
            overlapping_work = VacationRequest.objects.filter(
                employee=vacation.employee,
                leave_type='WORK',
                start_date__lte=vacation.end_date,
                end_date__gte=vacation.start_date
            )
            deleted_count = overlapping_work.count()
            if deleted_count > 0:
                overlapping_work.delete()
                print(f"[AUTO DELETE] {vacation.employee.first_name}의 근무일 {deleted_count}건 자동 삭제됨")

        # 상태 업데이트 및 기록 시간
        vacation.status = new_status
        vacation.reviewed_at = timezone.now()
        vacation.save()

        serializer = VacationRequestSerializer(vacation)
        return Response(serializer.data, status=status.HTTP_200_OK)