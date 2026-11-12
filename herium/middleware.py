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


def _host_allowed(host):
    name = (host or "").split(":")[0].lower()
    if not name:
        return False
    allowed = getattr(settings, "ALLOWED_HOSTS", []) or []
    for rule in allowed:
        rule = (rule or "").lower()
        if rule == "*":
            return True
        if rule.startswith("."):
            if name == rule[1:] or name.endswith(rule):
                return True
        elif name == rule:
            return True
    return False


class TrustCsrfOriginMiddleware:
    """허용된 호스트의 자기 origin만 CSRF 신뢰 목록에 넣습니다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if not _host_allowed(host):
            return self.get_response(request)
        proto = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip()
        if not proto:
            proto = "https" if request.is_secure() else "http"
        origin = f"{proto}://{host}"
        origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])
        if origin not in origins:
            origins.append(origin)
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
        response.headers["X-XSS-Protection"] = "1; mode=block"
        extra_scripts = " ".join(getattr(settings, "CSP_EXTRA_SCRIPT_SRC", ()) or ())
        extra_styles = " ".join(getattr(settings, "CSP_EXTRA_STYLE_SRC", ()) or ())
        response.headers["Content-Security-Policy"] = "; ".join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://dapi.kakao.com https://t1.daumcdn.net https://oapi.map.naver.com https://maps.googleapis.com"
            + (f" {extra_scripts}" if extra_scripts else ""),
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com"
            + (f" {extra_styles}" if extra_styles else ""),
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com data:",
            "img-src 'self' data: blob: https://res.cloudinary.com https://*.cloudinary.com https://*.googleapis.com https://*.gstatic.com https://maps.gstatic.com https://*.ggpht.com https://*.kakao.com https://*.kakaocdn.net https://*.daumcdn.net https://*.pstatic.net https://*.naver.com",
            "connect-src 'self' https://dapi.kakao.com https://*.kakao.com https://oapi.map.naver.com https://*.naver.com https://maps.googleapis.com",
            "frame-src 'self' https://www.google.com https://maps.google.com https://www.google.com/maps https://map.kakao.com https://dapi.kakao.com https://map.naver.com https://www.google.com/maps/embed",
            "child-src 'self' https://www.google.com https://maps.google.com https://map.kakao.com https://map.naver.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'",
            "form-action 'self'",
        ])
        return response
