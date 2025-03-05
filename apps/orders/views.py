from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class OrderListView(APIView):
    def get(self, request):
        orders = [
            {"id": 1, "item": "Laptop", "quantity": 2},
            {"id": 2, "item": "Mouse", "quantity": 5},
        ]
        return Response(orders, status=status.HTTP_200_OK)