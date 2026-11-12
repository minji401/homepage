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
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")
_running_tests = "test" in sys.argv


def _normalize_host(value):
    host = (value or "").strip().strip('"').strip("'").lower()
    if not host:
        return ""
    if "://" in host:
        host = (urlparse(host).hostname or "").strip().lower()
    else:
        host = host.split("/")[0].strip()
        if "@" in host:
            host = host.rsplit("@", 1)[-1]
        host = host.split(":")[0].strip()
    if host.startswith("*."):
        host = "." + host[2:]
    return host


def _split_host_values(raw):
    text = (raw or "").replace("\n", ",").replace(";", ",")
    hosts = []
    for part in text.split(","):
        host = _normalize_host(part.strip())
        if host:
            hosts.append(host)
    return hosts


_REQUIRED_HOSTS = [
    "heriumcare.com",
    "www.heriumcare.com",
    ".heriumcare.com",
    ".onrender.com",
    "localhost",
    "127.0.0.1",
]
ALLOWED_HOSTS = []
for _host in _REQUIRED_HOSTS + _split_host_values(os.getenv("ALLOWED_HOSTS") or ""):
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)
_render_host = _normalize_host(os.environ.get("RENDER_EXTERNAL_HOSTNAME", ""))
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)
if _running_tests:
    for _host in ("testserver", "localhost", "127.0.0.1"):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)

ADMIN_URL_PATH = (os.getenv("ADMIN_URL_PATH") or "herium-control-99").strip().strip("/") or "herium-control-99"

if not DEBUG and not _running_tests:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "corsheaders",
    "accounts.apps.AccountsConfig",
    "cms.apps.CmsConfig",
    "pages",
    "axes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "herium.middleware.StagingAuthMiddleware",
    "herium.middleware.SecurityHeadersMiddleware",
    "herium.middleware.TrustCsrfOriginMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
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
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.password_validators.SharedPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
PASSWORD_RESET_TIMEOUT = 3600

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static_collected"] if (BASE_DIR / "static_collected").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login.html"

# SecurityHeadersMiddleware CSP extras (FullCalendar 등)
CSP_EXTRA_SCRIPT_SRC = (
    "https://cdn.jsdelivr.net",
    "https://unpkg.com",
)
CSP_EXTRA_STYLE_SRC = (
    "https://cdn.jsdelivr.net",
    "https://unpkg.com",
)
LOGIN_REDIRECT_URL = "/mypage/"
LOGOUT_REDIRECT_URL = "/main.html"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "accounts.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_ENABLED = not _running_tests
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = "herium.axes_lockout.lockout_response"
AXES_IPWARE_META_PRECEDENCE_ORDER = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")
AXES_IPWARE_PROXY_COUNT = 1

MEDIA_URL = "/uploads/"
MEDIA_ROOT = BASE_DIR / "uploads"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "").strip()
CLOUDINARY_CLOUD_NAME = (
    os.environ.get("CLOUDINARY_CLOUD_NAME")
    or os.environ.get("CLOUD_NAME")
    or os.environ.get("cloud_name")
    or ""
).strip()
CLOUDINARY_API_KEY = (os.environ.get("CLOUDINARY_API_KEY") or os.environ.get("api_key") or "").strip()
CLOUDINARY_API_SECRET = (os.environ.get("CLOUDINARY_API_SECRET") or os.environ.get("api_secret") or "").strip()

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
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
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://heriumcare.com",
    "https://www.heriumcare.com",
    "https://hyundaimedi.com",
    "https://www.hyundaimedi.com",
]
CSRF_TRUSTED_ORIGINS = [
    "https://heriumcare.com",
    "https://www.heriumcare.com",
    "https://hyundaimedi.com",
    "https://www.hyundaimedi.com",
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
if os.environ.get("RENDER") or (not DEBUG and not _running_tests):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "security": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "security",
        }
    },
    "loggers": {
        "herium.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        }
    },
}
_log_dir = BASE_DIR / "logs"
try:
    _log_dir.mkdir(exist_ok=True)
    LOGGING["handlers"]["security_file"] = {
        "class": "logging.FileHandler",
        "filename": str(_log_dir / "security.log"),
        "encoding": "utf-8",
        "formatter": "security",
    }
    LOGGING["loggers"]["herium.security"]["handlers"].append("security_file")
except OSError:
    pass
