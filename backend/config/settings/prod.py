"""Production settings. DJANGO_SETTINGS_MODULE=config.settings.prod

Everything here should be strict-by-default; loosen only via env vars that
a deploy explicitly sets, never by editing this file per environment.
"""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
