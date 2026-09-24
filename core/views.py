import json

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from pydantic import ValidationError

from .models import Task
from .schemas import TaskCreateSchema


def home(request):
    return render(request, "core/home.html")


def healthz(request):
    """Checks DB and cache (Redis) connectivity, not just that the process is up."""
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - health check reports any failure
        checks["database"] = f"error: {exc}"

    try:
        cache.set("healthz", "ok", timeout=5)
        checks["cache"] = "ok" if cache.get("healthz") == "ok" else "error: unexpected value"
    except Exception as exc:  # noqa: BLE001
        checks["cache"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "ok" if healthy else "error", "checks": checks}, status=200 if healthy else 503)


def task_list(request):
    error = None

    if request.method == "POST":
        try:
            data = TaskCreateSchema(title=request.POST.get("title", ""))
            Task.objects.create(title=data.title)
            return redirect("core:task_list")
        except ValidationError as exc:
            error = exc.errors()[0]["msg"]

    tasks = Task.objects.all()
    return render(request, "core/task_list.html", {"tasks": tasks, "error": error})


def api_create_task(request):
    """JSON API demonstrating pydantic validation outside the form-POST path."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
        data = TaskCreateSchema(**payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    task = Task.objects.create(title=data.title)
    return JsonResponse({"id": task.id, "title": task.title, "done": task.done}, status=201)
