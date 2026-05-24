from django.http import JsonResponse
from rest_framework.response import Response


class MiddlewareAuthorization:
    @staticmethod
    def handle_error(response: Response):
        """Return a JsonResponse with a standardized auth error envelope."""
        data = getattr(response, "data", {})
        message = data.get(
            "detail", "No se proporcionaron credenciales de autenticación."
        )
        if message == "Authentication credentials were not provided.":
            message = "No se proporcionaron credenciales de autenticación."

        payload = {
            "success": False,
            "status": 401,
            "message": message,
        }
        return JsonResponse(payload, status=401)
