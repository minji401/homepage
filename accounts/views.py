import json
import secrets
import string

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Profile
from .shared_users import (
    SharedAuthError,
    create_shared_user,
    find_local_by_login,
    get_shared_by_phone,
    get_shared_by_username,
    login_with_shared,
    normalize_phone,
    shared_enabled,
    shared_expected,
    shared_matches_login,
    sync_local_user,
    update_shared_password,
    username_from_note,
)


def _json_body(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def _wants_json(request):
    return request.content_type and "application/json" in request.content_type


def _get_profile(user):
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None


def _profile_payload(user):
    profile = _get_profile(user)
    is_admin = bool(user.is_staff or (profile and profile.role == Profile.ROLE_ADMIN))
    return {
        "authenticated": True,
        "id": user.username,
        "name": (profile.name if profile and profile.name else user.first_name) or user.username,
        "phone": profile.phone if profile else "",
        "email": user.email or "",
        "is_admin": is_admin,
        "role": profile.role if profile else Profile.ROLE_MEMBER,
        "status": profile.status if profile else Profile.STATUS_ACTIVE,
    }


@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated:
        return redirect("/main.html")
    return render(request, "login.html")


@csrf_exempt
@require_POST
def login_api(request):
    data = _json_body(request)
    user_id = (data.get("id") or data.get("username") or "").strip()
    password = data.get("password") or ""
    if not user_id or not password:
        return JsonResponse({"ok": False, "message": "아이디와 비밀번호를 입력해 주세요."}, status=400)

    if shared_expected() and not shared_enabled():
        return JsonResponse(
            {"ok": False, "message": "공유 회원 DB가 연결되지 않았습니다. Render DATABASE_URL을 확인해 주세요."},
            status=503,
        )
    if shared_enabled():
        try:
            user = login_with_shared(request, user_id, password)
        except SharedAuthError as exc:
            return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
        payload = _profile_payload(user)
        return JsonResponse({"ok": True, "user": payload, "redirect": "/staff/" if payload["is_admin"] else "/main.html"})

    try:
        existing = User.objects.select_related("profile").get(username=user_id)
    except User.DoesNotExist:
        existing = find_local_by_login(user_id)
        if existing is None:
            return JsonResponse({"ok": False, "message": "등록되지 않은 아이디입니다."}, status=400)
    except OperationalError:
        return JsonResponse({"ok": False, "message": "회원 DB가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요."}, status=503)

    profile = _get_profile(existing)
    if profile and profile.status == Profile.STATUS_SUSPENDED:
        return JsonResponse({"ok": False, "message": "정지된 계정입니다. 관리자에게 문의해 주세요."}, status=403)
    if profile and profile.status == Profile.STATUS_WITHDRAWN:
        return JsonResponse({"ok": False, "message": "탈퇴 처리된 계정입니다."}, status=403)
    if not existing.is_active:
        return JsonResponse({"ok": False, "message": "정지된 계정입니다. 관리자에게 문의해 주세요."}, status=403)

    user = authenticate(request, username=existing.username, password=password)
    if user is None:
        return JsonResponse({"ok": False, "message": "비밀번호가 일치하지 않습니다."}, status=400)

    login(request, user)
    payload = _profile_payload(user)
    return JsonResponse({"ok": True, "user": payload, "redirect": "/staff/" if payload["is_admin"] else "/main.html"})


@ensure_csrf_cookie
def signup_page(request):
    if request.user.is_authenticated:
        return redirect("/main.html")
    return render(request, "signup.html")


@csrf_exempt
@require_POST
def signup_api(request):
    data = _json_body(request)
    user_id = (data.get("id") or "").strip()
    password = data.get("password") or ""
    password_confirm = data.get("passwordConfirm") or data.get("password_confirm") or ""
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    agree = data.get("agree") in (True, "true", "on", "1", 1)

    if not user_id or not password or not name or not phone:
        return JsonResponse({"ok": False, "message": "아이디, 비밀번호, 이름, 연락처는 필수입니다."}, status=400)
    if len(user_id) < 4:
        return JsonResponse({"ok": False, "message": "아이디는 4자 이상 입력해 주세요."}, status=400)
    if len(password) < 4:
        return JsonResponse({"ok": False, "message": "비밀번호는 4자 이상 입력해 주세요."}, status=400)
    if password_confirm and password != password_confirm:
        return JsonResponse({"ok": False, "message": "비밀번호가 서로 다릅니다."}, status=400)
    if not agree:
        return JsonResponse({"ok": False, "message": "이용약관 및 개인정보 처리에 동의해 주세요."}, status=400)
    digits = normalize_phone(phone)
    if len(digits) < 10:
        return JsonResponse({"ok": False, "message": "올바른 휴대폰 번호를 입력해 주세요."}, status=400)
    try:
        if User.objects.filter(username=user_id).exists():
            return JsonResponse({"ok": False, "message": "이미 사용 중인 아이디입니다."}, status=400)
    except OperationalError:
        return JsonResponse({"ok": False, "message": "회원 DB가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요."}, status=503)

    if shared_expected() and not shared_enabled():
        return JsonResponse(
            {"ok": False, "message": "공유 회원 DB가 연결되지 않았습니다. Render DATABASE_URL을 확인해 주세요."},
            status=503,
        )
    if shared_expected() or shared_enabled():
        try:
            create_shared_user(name=name, phone=digits, password=password, username=user_id)
        except SharedAuthError as exc:
            return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)

    user = User.objects.create_user(
        username=user_id,
        password=password,
        email=email,
        first_name=name,
    )
    Profile.objects.update_or_create(
        user=user,
        defaults={"name": name, "phone": digits, "role": Profile.ROLE_MEMBER, "status": Profile.STATUS_ACTIVE},
    )
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def logout_api(request):
    logout(request)
    if _wants_json(request):
        return JsonResponse({"ok": True})
    return redirect("/main.html")


@ensure_csrf_cookie
@require_GET
def me_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})
    return JsonResponse(_profile_payload(request.user))


@ensure_csrf_cookie
def find_page(request):
    return render(request, "find-account.html")


@csrf_exempt
@require_http_methods(["POST"])
def find_api(request):
    data = _json_body(request)
    find_type = (data.get("type") or request.GET.get("type") or "id").strip()
    phone = (data.get("phone") or "").strip()

    digits = normalize_phone(phone)
    if find_type == "password":
        user_id = (data.get("id") or "").strip()
        if not user_id or not phone:
            return JsonResponse({"ok": False, "message": "아이디와 연락처를 입력해 주세요."}, status=400)

        user = None
        try:
            user = User.objects.select_related("profile").get(username=user_id)
            profile_phone = normalize_phone(getattr(_get_profile(user), "phone", "") or "")
            if digits and profile_phone and digits != profile_phone:
                user = None
        except User.DoesNotExist:
            user = find_local_by_login(user_id)
            if user is not None:
                profile_phone = normalize_phone(getattr(_get_profile(user), "phone", "") or "")
                if digits and profile_phone and digits != profile_phone:
                    user = None

        shared = None
        if shared_enabled():
            try:
                if digits:
                    shared = get_shared_by_phone(digits)
                if shared is None:
                    shared = get_shared_by_username(user_id)
            except SharedAuthError as exc:
                return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
            if shared is not None and digits and normalize_phone(shared.phone) != digits:
                shared = None
            if shared is not None and not shared_matches_login(shared, user_id):
                return JsonResponse({"ok": False, "message": "일치하는 회원 정보가 없습니다."}, status=400)
        if user is None and shared is not None:
            hint = (shared.username or "").strip() or username_from_note(shared.herium_note) or user_id
            user = sync_local_user(shared, username_hint=hint)
        if user is None:
            return JsonResponse({"ok": False, "message": "일치하는 회원 정보가 없습니다."}, status=400)

        alphabet = string.ascii_letters + string.digits
        temp = "".join(secrets.choice(alphabet) for _ in range(8))
        user.set_password(temp)
        user.save(update_fields=["password"])
        if shared is not None:
            update_shared_password(shared, temp)
        elif shared_enabled() and digits:
            try:
                create_shared_user(
                    name=(_get_profile(user).name if _get_profile(user) else user.first_name) or user.username,
                    phone=digits,
                    password=temp,
                    username=user.username,
                )
            except SharedAuthError:
                pass
        return JsonResponse({
            "ok": True,
            "message": f"임시 비밀번호는 {temp} 입니다. 로그인 후 변경해 주세요.",
        })

    name = (data.get("name") or "").strip()
    if not name or not phone:
        return JsonResponse({"ok": False, "message": "이름과 연락처를 입력해 주세요."}, status=400)
    if shared_enabled() and digits:
        try:
            shared = get_shared_by_phone(digits)
        except SharedAuthError as exc:
            return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
        if shared is not None and shared.name.replace(" ", "") == name.replace(" ", ""):
            shown = (shared.username or "").strip() or username_from_note(shared.herium_note) or shared.phone
            if shown == shared.phone or shown == normalize_phone(shared.phone):
                message = f"회원님의 로그인 번호는 {shared.phone} 입니다. 헤리움 아이디가 있으면 아이디로도 로그인할 수 있습니다."
            else:
                message = f"회원님의 아이디는 {shown} 입니다."
            return JsonResponse({"ok": True, "id": shown, "message": message})
    try:
        user = User.objects.select_related("profile").get(profile__name=name, profile__phone=phone)
    except User.DoesNotExist:
        user = find_local_by_login(digits)
        if user is None or not _get_profile(user) or _get_profile(user).name != name:
            return JsonResponse({"ok": False, "message": "일치하는 회원 정보가 없습니다."}, status=400)
    return JsonResponse({"ok": True, "id": user.username, "message": f"회원님의 아이디는 {user.username} 입니다."})
