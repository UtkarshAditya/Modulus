# Make sure the Celery app is loaded whenever Django starts, so that
# shared_task decorators across apps pick it up.
from .celery import app as celery_app

__all__ = ("celery_app",)
