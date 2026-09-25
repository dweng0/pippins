from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Checks real DB connectivity, not just that the process is up."""
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - health check reports any failure
        checks["database"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "ok" if healthy else "error", "checks": checks}, status=200 if healthy else 503)

