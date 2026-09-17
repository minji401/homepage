from django.utils.deprecation import MiddlewareMixin

from .models import VisitLog

SKIP_PREFIXES = (
    "/staff",
    "/accounts",
    "/admin",
    "/api/",
    "/img/",
)
SKIP_SUFFIXES = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff2")


class VisitLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.method != "GET" or response.status_code >= 400:
            return response
        path = request.path or "/"
        if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
            return response
        if path.endswith(SKIP_SUFFIXES):
            return response
        try:
            if not request.session.session_key:
                request.session.save()
            VisitLog.objects.create(
                path=path[:300],
                referer=(request.META.get("HTTP_REFERER") or "")[:400],
                session_key=request.session.session_key or "",
            )
        except Exception:
            pass
        return response
