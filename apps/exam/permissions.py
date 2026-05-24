from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsExamAuthenticated(BasePermission):
    message = "Autenticación requerida para acceder a la evaluación."

    def has_permission(self, request: Request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)
