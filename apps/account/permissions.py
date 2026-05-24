from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import User


class IsFirebaseAuthenticated(BasePermission):
    """
    Permite acceso solo a usuarios autenticados cuya cuenta
    esté vinculada a Firebase (poseen firebase_uid).
    """

    message = "Autenticación requerida. Inicia sesión con Google."

    def has_permission(self, request: Request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "firebase_uid", None)
        )


class IsTeacher(BasePermission):
    message = "Permiso denegado. Solo disponible para profesores."

    def has_permission(self, request: Request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == User.Role.TEACHER
        )


class IsStudent(BasePermission):
    message = "Permiso denegado. Solo disponible para estudiantes."

    def has_permission(self, request: Request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == User.Role.STUDENT
        )


class IsAuthenticatedAndTeacher(IsTeacher):
    pass


class IsAuthenticatedAndStudent(IsStudent):
    pass
