from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer
from django.contrib.auth.hashers import make_password

User = get_user_model()
# User Serializer for Signup
class RegisterSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])  # Hash password
        return super().create(validated_data)
