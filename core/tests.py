import json

import pytest
from django.urls import reverse

from core.models import Task
from core.schemas import TaskCreateSchema
from pydantic import ValidationError


@pytest.mark.django_db
def test_task_list_renders(client):
    response = client.get(reverse("core:task_list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get(reverse("core:healthz"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_task_created_via_form_post(client):
    response = client.post(reverse("core:task_list"), {"title": "Write tests"})
    assert response.status_code == 302
    assert Task.objects.filter(title="Write tests").exists()


@pytest.mark.django_db
def test_blank_task_title_rejected(client):
    response = client.post(reverse("core:task_list"), {"title": "   "})
    assert response.status_code == 200
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_api_create_task_valid_payload(client):
    response = client.post(
        reverse("core:api_create_task"),
        data=json.dumps({"title": "From API"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert Task.objects.filter(title="From API").exists()


@pytest.mark.django_db
def test_api_create_task_rejects_missing_title(client):
    response = client.post(
        reverse("core:api_create_task"),
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert Task.objects.count() == 0


def test_task_schema_rejects_blank_title():
    with pytest.raises(ValidationError):
        TaskCreateSchema(title="   ")
