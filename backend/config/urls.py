from django.contrib import admin
from django.urls import include, path

from .health import healthz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.postings.urls")),
    path("api/", include("apps.moderation.urls")),
]
