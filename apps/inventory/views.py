from rest_framework.views import APIView
from rest_framework.response import Response
from .models import InventoryItem
from .serializers import InventoryItemSerializer

class InventoryListView(APIView):
    def get(self, request):
        items = InventoryItem.objects.all()
        serializer = InventoryItemSerializer(items, many=True)
        return Response(serializer.data)