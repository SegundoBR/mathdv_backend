import time

from home.system_monitor import record_request_metric


class SystemMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - started_at) * 1000

        if request.path.startswith("/api/"):
            record_request_metric(
                path=request.path,
                method=request.method,
                status_code=getattr(response, "status_code", 200),
                duration_ms=duration_ms,
            )

        return response
