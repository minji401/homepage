from django.http import JsonResponse
from django.views.csrf import csrf_failure as django_csrf_failure


def csrf_failure(request, reason=""):
    accept = request.META.get("HTTP_ACCEPT") or ""
    content_type = request.content_type or ""
    wants_json = (
        "application/json" in accept
        or "application/json" in content_type
        or request.path.startswith("/accounts/")
        or request.path.startswith("/api/")
    )
    if wants_json:
        return JsonResponse(
            {
                "ok": False,
                "message": "보안 검증에 실패했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.",
            },
            status=403,
        )
    return django_csrf_failure(request, reason=reason)
