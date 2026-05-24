from rest_framework import serializers

from .models import User


class GoogleAuthSerializer(serializers.Serializer):
    """Serializer para recibir el Firebase ID Token desde el frontend."""

    id_token = serializers.CharField(
        required=True,
        write_only=True,
        help_text="Firebase ID Token obtenido tras autenticar con Google.",
    )


class UserSerializer(serializers.ModelSerializer):
    """Serializer de lectura para retornar información básica del usuario."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "photo_url"]
        read_only_fields = ["id", "email", "first_name", "last_name", "photo_url"]


class TeacherLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TeacherUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "photo_url",
            "role",
        ]
        read_only_fields = fields
