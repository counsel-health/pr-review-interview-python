"""
Django settings for the Counsel messaging backend.

This is a local development / interview exercise app: DEBUG defaults on, the
secret key has a development fallback, and there is no authentication (see
REST_FRAMEWORK below).
"""

from __future__ import annotations

import os
from pathlib import Path

from counsel.db import database_config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-not-for-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Deliberately minimal: no auth, no sessions, no admin, and no contenttypes —
# nothing here uses them, and leaving them out keeps the schema to the tables
# this app actually owns.
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "api",
    "jobs",
]

# No session/auth/messages middleware: the app has no login and no server-side
# session state. CSRF is likewise absent — see the REST_FRAMEWORK note.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "counsel.urls"
WSGI_APPLICATION = "counsel.wsgi.application"
ASGI_APPLICATION = "counsel.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

DATABASES = {"default": database_config()}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"

# The acting user is chosen client-side and sent as `userId` in the request
# body; the server trusts it. There is intentionally no authentication,
# authorization, or CSRF protection in this demo.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "api.exceptions.counsel_exception_handler",
    "UNAUTHENTICATED_USER": None,
}

# Shared secret for Relay webhook signatures.
RELAY_WEBHOOK_SECRET = os.environ.get("RELAY_WEBHOOK_SECRET")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
