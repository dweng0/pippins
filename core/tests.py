import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_renders(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get(reverse("core:healthz"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
