"""
Shared settings. dev.py / prod.py layer environment-specific overrides on top.
Every secret/host-dependent value comes from the environment, never hardcoded,
so the same image runs locally (docker-compose) and on the EC2 box.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
from whitenoise.compress import Compressor

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django_htmx",
    "core",
    "player",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "stackcx"),
        "USER": os.environ.get("POSTGRES_USER", "stackcx"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "stackcx"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Sessions live in Postgres so a deploy doesn't orphan every Listener (ADR-0001, #23).
# Nothing needs a shared cache yet; per-process LocMem is enough.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

SESSION_ENGINE = "django.contrib.sessions.backends.db"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Content-hashed names: WhiteNoise (and Cloudflare) cache them as immutable, so a deploy can
    # never serve stale CSS/JS. Needs collectstatic first; DEBUG serves plain names.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# mp3 isn't in WhiteNoise's default skip list; gzip saves <1.5% on audio, so don't spend collectstatic time on it.
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = (*Compressor.SKIP_COMPRESS_EXTENSIONS, "mp3")
# Hashed names are served immutable for a year; anything requested by its unhashed
# name keeps WhiteNoise's 60s default, so nothing can go stale for long.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
