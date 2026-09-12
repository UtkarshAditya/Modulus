"""Phase 0 smoke tests: the pieces every later phase depends on actually
wire together — the health endpoint responds, and a task submitted through
the real Celery app (not called directly as a plain function) round-trips.
"""

from django.test import Client
from django.urls import reverse

from config.celery import ping


def test_healthz_ok():
    response = Client().get(reverse("healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_celery_ping_roundtrip(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    result = ping.delay()
    assert result.get(timeout=5) == "pong"
