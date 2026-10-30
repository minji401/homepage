import logging
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger("herium")

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_files():
    for name in (".env", ".env.local"):
        path = BASE_DIR / name
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and os.environ.get(key) is None:
                os.environ[key] = value


_load_env_files()

_DEV_SECRET = "django-insecure-herium-local-dev-only-change-later"
SECRET_KEY = os.environ.get("SECRET_KEY", "" if os.environ.get("RENDER") else _DEV_SECRET)
if os.environ.get("RENDER") and (not SECRET_KEY or SECRET_KEY == _DEV_SECRET):
    raise RuntimeError("RENDER 환경에는 SECRET_KEY 환경변수가 필요합니다.")
DEBUG = os.environ.get("DEBUG", "false" if os.environ.get("RENDER") else "true").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "ALLOWED_HOSTS",
        "heriumcare.com,www.heriumcare.com,localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "cms.apps.CmsConfig",
    "pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "herium.middleware.StagingAuthMiddleware",
    "herium.middleware.SecurityHeadersMiddleware",
    "herium.middleware.TrustCsrfOriginMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "cms.middleware.VisitLogMiddleware",
]

ROOT_URLCONF = "herium.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR, BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cms.context_processors.public_cms",
            ],
        },
    },
]

WSGI_APPLICATION = "herium.wsgi.application"


def _postgres_from_url(url):
    url = (url or "").strip().strip('"').strip("'")
    if not url:
        return None
    parsed = urlparse(url)
    name = unquote((parsed.path or "").lstrip("/").split("?")[0])
    query = parse_qs(parsed.query or "")
    if not name:
        name = (query.get("dbname") or query.get("database") or [""])[0]
    if not name:
        return None
    sslmode = (os.environ.get("PGSSLMODE") or "").strip() or (query.get("sslmode") or [""])[0] or "prefer"
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": sslmode},
    }


_running_tests = "test" in sys.argv
_db_url = (os.environ.get("DATABASE_URL") or os.environ.get("SHARED_DATABASE_URL") or "").strip()
_pg = _postgres_from_url(_db_url)

if _running_tests:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
elif _pg:
    DATABASES = {
        "default": dict(_pg),
        "shared": dict(_pg),
    }
    DATABASE_ROUTERS = ["accounts.db_router.SharedDatabaseRouter"]
    logger.info("postgres configured name=%s host_set=%s", _pg["NAME"], bool(_pg["HOST"]))
else:
    raise RuntimeError("DATABASE_URL이 필요합니다. SQLite는 쓰지 않고 Neon Postgres만 사용합니다.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static_collected"] if (BASE_DIR / "static_collected").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login.html"
LOGIN_REDIRECT_URL = "/main.html"
LOGOUT_REDIRECT_URL = "/main.html"

MEDIA_URL = "/uploads/"
MEDIA_ROOT = BASE_DIR / "uploads"
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SITE_URL = os.environ.get("SITE_URL", "https://heriumcare.com").rstrip("/")
JWT_SECRET = os.environ.get("JWT_SECRET") or os.environ.get("DATA_ENCRYPTION_KEY") or SECRET_KEY
SMS_API_URL = os.environ.get("SMS_API_URL", "")
SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
SMS_SENDER = os.environ.get("SMS_SENDER", "")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.environ.get("EMAIL_FROM", "") or EMAIL_HOST_USER or "noreply@heriumcare.com"
CSRF_FAILURE_VIEW = "herium.csrf.csrf_failure"
CSRF_TRUSTED_ORIGINS = [
    "https://heriumcare.com",
    "https://www.heriumcare.com",
    "https://*.onrender.com",
    "https://*.ngrok-free.app",
    "https://*.ngrok.io",
    "https://*.trycloudflare.com",
    "https://*.loca.lt",
]
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if _render_host:
    CSRF_TRUSTED_ORIGINS.append(f"https://{_render_host}")
for _origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(","):
    _origin = _origin.strip()
    if _origin and _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
