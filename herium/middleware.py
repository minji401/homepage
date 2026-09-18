from django.conf import settings


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
