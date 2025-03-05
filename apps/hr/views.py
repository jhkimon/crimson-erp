from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class EmployeeListView(APIView):
    def get(self, request):
        employees = [
            {"id": 1, "name": "John Doe", "position": "Manager"},
            {"id": 2, "name": "Jane Smith", "position": "Developer"},
        ]
        return Response(employees, status=status.HTTP_200_OK)