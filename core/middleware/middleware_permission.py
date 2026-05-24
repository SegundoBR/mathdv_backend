from django.http import JsonResponse
from rest_framework.response import Response


class MiddlewarePermission:
    @staticmethod
    def handle_error(response: Response):
        payload = {
            "success": False,
            "status": 403,
            "message": "No tienes permisos para realizar esta acción.",
        }
        return JsonResponse(payload, status=403)
