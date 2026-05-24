import logging
import time

from django.http import JsonResponse


class HandleMiddlewares:
    """
    Simplified middleware for request/response logging and timing.

    Response formatting is now handled by DRF's exception handler and renderer
    (apps.utils.api_response), making this middleware much simpler and safer.
    """

    logger = logging.getLogger("api.request")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()

        try:
            response = self.get_response(request)

            # Log API requests
            if request.path.startswith("/api/"):
                duration_ms = (time.perf_counter() - started_at) * 1000
                self.logger.info(
                    "API %s %s status=%s origin=%s auth=%s user=%s role=%s duration_ms=%.2f",
                    request.method,
                    request.path,
                    response.status_code,
                    request.headers.get("Origin", "-"),
                    "yes" if request.headers.get("Authorization") else "no",
                    getattr(request.user, "email", "anonymous"),
                    getattr(request.user, "role", "-"),
                    duration_ms,
                )

            return response

        except Exception:
            # Let Django's middleware and exception handler deal with unhandled exceptions
            # The custom exception handler will format errors properly
            if request.path.startswith("/api/"):
                duration_ms = (time.perf_counter() - started_at) * 1000
                self.logger.exception(
                    "API %s %s status=500 origin=%s auth=%s duration_ms=%.2f",
                    request.method,
                    request.path,
                    request.headers.get("Origin", "-"),
                    "yes" if request.headers.get("Authorization") else "no",
                    duration_ms,
                )

            raise
