from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.utils import timezone


def health_view(request):
    db_ok = True
    db_error = ""

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError as exc:
        db_ok = False
        db_error = str(exc)

    status_code = 200 if db_ok else 503
    payload = {
        "status": "ok" if db_ok else "degraded",
        "timestamp": timezone.now().isoformat(),
        "checks": {
            "database": {
                "ok": db_ok,
                "error": db_error,
            }
        },
    }
    return JsonResponse(payload, status=status_code)
