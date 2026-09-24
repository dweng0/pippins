import os

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split(",")

# Set DJANGO_HTTPS=false only while the box is reachable over plain HTTP (before TLS
# is terminated in front of it, e.g. Cloudflare). Default is secure.
HTTPS = os.environ.get("DJANGO_HTTPS", "true").lower() == "true"

SECURE_SSL_REDIRECT = HTTPS
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7 if HTTPS else 0
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]
