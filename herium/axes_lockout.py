from django.http import JsonResponse
from django.shortcuts import render


LOCKOUT_MESSAGE = "비밀번호를 5회 연속으로 틀려 로그인이 잠겼습니다. 약 30분 뒤에 다시 시도해 주세요."


def lockout_response(request, credentials, *args, **kwargs):
    accept = request.META.get("HTTP_ACCEPT") or ""
    content_type = request.content_type or ""
    wants_json = (
        "application/json" in accept
        or "application/json" in content_type
        or request.path.startswith("/accounts/")
        or request.path.startswith("/api/")
    )
    if wants_json:
        return JsonResponse({"ok": False, "message": LOCKOUT_MESSAGE}, status=423)
    return render(request, "429.html", {"message": LOCKOUT_MESSAGE}, status=403)