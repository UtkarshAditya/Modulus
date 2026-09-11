import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("content_pipeline")

# Read CELERY_* settings from Django settings, using the CELERY_ namespace
# so celery config lives next to everything else in config/settings/.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every INSTALLED_APPS app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=False)
def ping(self):
    """Round-trip smoke test: worker liveness, broker, and result backend."""
    return "pong"
