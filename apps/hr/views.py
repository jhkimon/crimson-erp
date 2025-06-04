from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from .models import Employee
from .serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
    EmployeeDeactivateSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
        employees = Employee.objects.all()
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="직원 등록",
        request_body=EmployeeCreateSerializer,
        responses={
            201: EmployeeDetailSerializer(),
            400: "Bad Request"
        }
    )
    def post(self, request):
        """직원 등록"""
        serializer = EmployeeCreateSerializer(data=request.data)
        if serializer.is_valid():
            employee = serializer.save()
            response_serializer = EmployeeDetailSerializer(employee)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        employee = get_object_or_404(Employee, id=employee_id)
        serializer = EmployeeDetailSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="직원 정보 수정",
        request_body=EmployeeUpdateSerializer,
        responses={
            200: EmployeeDetailSerializer(),
            400: "Bad Request",
            404: "Not Found"
        }
    )
    def put(self, request, employee_id):
        """직원 정보 수정"""
        employee = get_object_or_404(Employee, id=employee_id)
        serializer = EmployeeUpdateSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            updated_employee = serializer.save()
            response_serializer = EmployeeDetailSerializer(updated_employee)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="직원 비활성화 (퇴사 처리)",
        responses={
            200: EmployeeDeactivateSerializer(),
            400: "Bad Request",
            404: "Not Found"
        }
    )
    def patch(self, request, employee_id):
        """직원 비활성화 (퇴사 처리)"""
        employee = get_object_or_404(Employee, id=employee_id)
        employee.is_active = False
        employee.status = 'inactive'
        employee.save()
        
        serializer = EmployeeDeactivateSerializer(employee, partial=True)
        return Response(serializer.data, status=status.HTTP_200_OK)