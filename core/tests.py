import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get(reverse("core:healthz"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"] == {"database": "ok"}


@pytest.mark.django_db
def test_sessions_are_stored_in_postgres(client):
    # Redis had no volume, so every deploy wiped sessions and orphaned Listeners (#23).
    from django.contrib.sessions.models import Session
    from django.core.cache import cache

    client.get("/")
    cache.clear()
    assert Session.objects.count() == 1
    client.get("/")
    assert Session.objects.count() == 1
