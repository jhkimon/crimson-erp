from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150, help_text="사용자 아이디")
    email = serializers.EmailField(help_text="이메일")
    password = serializers.CharField(write_only=True, help_text="비밀번호")
    first_name = serializers.CharField(max_length=50, help_text="이름")
    contact = serializers.CharField(max_length=20, help_text="연락처")
    class Meta:
        model = User
        fields = (
            "username", "email", "password", "first_name", "contact"
        )

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "contact", "role", "status"]
        read_only_fields = fields