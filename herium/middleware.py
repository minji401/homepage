import base64
import hmac
import os

from django.conf import settings
from django.http import HttpResponse


def registration_open():
    value = os.environ.get("ALLOW_REGISTRATION", "true").strip().lower()
    return value not in ("0", "false", "no")


def _staging_credentials():
    user = os.environ.get("STAGING_USER", "").strip()
    password = os.environ.get("STAGING_PASSWORD", "")
    if not user or not password:
        return None
    return user, password


def _same(left, right):
    a = left.encode("utf-8")
    b = right.encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def _basic_match(header, user, password):
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
    except Exception:
        return False
    given_user, sep, given_password = decoded.partition(":")
    if not sep:
        return False
    return _same(given_user, user) and _same(given_password, password)


class StagingAuthMiddleware:
    """STAGING_USER와 STAGING_PASSWORD가 둘 다 있을 때만 사이트 전체를 잠급니다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        creds = _staging_credentials()
        if creds is None or request.path == "/healthz":
            return self.get_response(request)
        user, password = creds
        if _basic_match(request.META.get("HTTP_AUTHORIZATION", ""), user, password):
            return self.get_response(request)
        response = HttpResponse("인증이 필요합니다.", status=401, content_type="text/plain; charset=utf-8")
        response["WWW-Authenticate"] = 'Basic realm="staging"'
        return response


class TrustCsrfOriginMiddleware:
    """구매한 도메인·프록시 환경에서도 CSRF Origin 검사를 통과시킵니다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])
        host = request.get_host()
        proto = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip()
        if not proto:
            proto = "https" if request.is_secure() else "http"

        extra = [
            (request.META.get("HTTP_ORIGIN") or "").rstrip("/"),
            f"{proto}://{host}",
            f"https://{host}",
            f"http://{host}",
        ]
        changed = False
        for origin in extra:
            if origin and origin not in origins:
                origins.append(origin)
                changed = True
        if changed:
            settings.CSRF_TRUSTED_ORIGINS = origins
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Content-Security-Policy"] = "; ".join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com data:",
            "img-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'",
            "form-action 'self'",
        ])
        return response
