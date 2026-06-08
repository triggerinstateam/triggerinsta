"""
Django settings for triggerflow backend.

This backend is a thin REST API over the *existing* Neon Postgres database that
Prisma owns (see ../frontend/prisma/schema.prisma). All models are managed=False;
Django never migrates these tables. Auth is handled by the Next.js frontend
(NextAuth); requests reach us through a server-side proxy that injects a shared
internal secret + the authenticated user's email.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG = env("DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "*").split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [h.strip() for h in env("CSRF_TRUSTED_ORIGINS", "").split(",") if h.strip()]

# Shared secret the Next.js proxy must present on every internal request.
INTERNAL_API_SECRET = env("INTERNAL_API_SECRET", "")

# Meta / Instagram + Groq config (read in views/services).
PAGE_ACCESS_TOKEN = env("PAGE_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = env("INSTAGRAM_ACCOUNT_ID")
FACEBOOK_APP_ID = env("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = env("FACEBOOK_APP_SECRET")
INSTAGRAM_REDIRECT_URI = env("INSTAGRAM_REDIRECT_URI")
GROQ_API_KEY = env("GROQ_API_KEY")
VERIFY_TOKEN = env("VERIFY_TOKEN", "triggerflow123")
GRAPH_API_VERSION = env("GRAPH_API_VERSION", "v19.0")


# Application definition — lean API-only stack (no contrib auth/sessions/admin,
# so Django never needs tables that don't exist in the Prisma-owned schema).
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "triggerflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "triggerflow.wsgi.application"


# Database — the existing Neon Postgres (Prisma-owned schema, managed=False models).
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    ),
}


# DRF: authenticate/authorize via the internal shared secret only.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.auth.InternalSecretAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "core.auth.IsInternalRequest",
    ],
    "UNAUTHENTICATED_USER": None,
}


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
