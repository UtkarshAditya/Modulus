"""Liveness/readiness endpoint used by Docker Compose, load balancers, and
the Phase 0 "docker compose up" smoke test. Deliberately dependency-light:
it does not touch the database so it stays up even if migrations haven't
run yet, which is what you want from a container healthcheck.
"""

from django.http import JsonResponse


def healthz(request):
    return JsonResponse({"status": "ok"})
