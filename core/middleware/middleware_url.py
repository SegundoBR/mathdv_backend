from django.http import JsonResponse


class MiddlewareURL:
    @staticmethod
    def handle_error(request):
        return JsonResponse(
            {"success": False, "status": 404, "message": "La URL no existe."},
            status=404,
        )
