import logging

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsAuthenticatedAndTeacher
from .serializers import (
    GoogleAuthSerializer,
    TeacherLoginSerializer,
    TeacherUserSerializer,
    UserSerializer,
)
from .services import (
    FirebaseTokenError,
    get_or_create_user,
    register_student_login_activity,
    verify_firebase_token,
)

logger = logging.getLogger(__name__)


class GoogleAuthView(APIView):
    """
    POST /api/account/auth/google/

    Endpoint único de autenticación con Google mediante Firebase.
    Actúa como login y registro de forma transparente.

    El frontend nunca distingue si el usuario es nuevo o ya existía.

    Request body:
        {
            "id_token": "<Firebase ID Token>"
        }

    Response:
        {
            "access_token": "...",
            "refresh_token": "...",
            "user": {
                "id": "...",
                "email": "...",
                "first_name": "...",
                "last_name": "...",
                "photo_url": "..."
            }
        }
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere auth previa

    def post(self, request: Request) -> Response:
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        id_token: str = serializer.validated_data["id_token"]

        # 1. Verificar token con Firebase Admin SDK
        try:
            firebase_data = verify_firebase_token(id_token)
        except FirebaseTokenError as exc:
            return Response(
                {"detail": exc.detail},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 2. Obtener o crear usuario (login + registro unificado)
        user = get_or_create_user(firebase_data)
        register_student_login_activity(user=user)

        # 3. Emitir tokens JWT propios del backend
        refresh = RefreshToken.for_user(user)

        logger.info("Autenticación exitosa para usuario: %s", user.email)

        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class UserProfileView(APIView):
    """
    GET /api/account/profile/

    Retorna los datos del perfil del usuario autenticado.

    Response:
        {
            "id": "...",
            "email": "...",
            "first_name": "...",
            "last_name": "...",
            "photo_url": "..."
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeacherLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = TeacherLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request=request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Credenciales inválidas."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Usuario inactivo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if getattr(user, "role", None) != user.Role.TEACHER:
            return Response(
                {"detail": "Acceso denegado para backoffice."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": TeacherUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class TeacherMeView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        return Response(
            TeacherUserSerializer(request.user).data, status=status.HTTP_200_OK
        )
