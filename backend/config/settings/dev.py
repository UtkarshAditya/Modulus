"""Local development settings. DJANGO_SETTINGS_MODULE=config.settings.dev"""

from .base import *  # noqa: F401,F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
