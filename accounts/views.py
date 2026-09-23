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
    needs_guardian_prompt,
    normalize_phone,
    resolve_shared_login,
    set_guardian_name,
    shared_enabled,
    shared_expected,
    shared_matches_login,
    sync_local_user,
    update_shared_password,
    update_shared_phone,
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
        "name": (profile.name if profile and profile.name else "") or "",
        "phone": profile.phone if profile else "",
        "email": user.email or "",
        "is_admin": is_admin,
        "needs_guardian": False,
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
        shared = resolve_shared_login(user_id, user)
        needs = needs_guardian_prompt(shared, user)
        payload["needs_guardian"] = needs
        if needs:
            payload["name"] = ""
            redirect = "/guardian.html"
        elif payload["is_admin"]:
            redirect = "/staff/"
        else:
            redirect = "/main.html"
        return JsonResponse({"ok": True, "user": payload, "redirect": redirect})

    try:
        existing = User.objects.select_related("profile").get(username=user_id)
    except User.DoesNotExist:
        existing = find_local_by_login(user_id)
        if existing is None:
            return JsonResponse({"ok": False, "message": "아이디 또는 비밀번호가 일치하지 않습니다."}, status=400)
    except OperationalError:
        return JsonResponse({"ok": False, "message": "회원 DB가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요."}, status=503)

    user = authenticate(request, username=existing.username, password=password)
    if user is None:
        return JsonResponse({"ok": False, "message": "아이디 또는 비밀번호가 일치하지 않습니다."}, status=400)
    profile = _get_profile(user)
    if profile and profile.status == Profile.STATUS_SUSPENDED:
        return JsonResponse({"ok": False, "message": "정지된 계정입니다. 관리자에게 문의해 주세요."}, status=403)
    if profile and profile.status == Profile.STATUS_WITHDRAWN:
        return JsonResponse({"ok": False, "message": "탈퇴 처리된 계정입니다."}, status=403)
    if not user.is_active:
        return JsonResponse({"ok": False, "message": "정지된 계정입니다. 관리자에게 문의해 주세요."}, status=403)

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
    payload = _profile_payload(request.user)
    if shared_enabled() and not payload["is_admin"]:
        shared = resolve_shared_login(request.user.username, request.user)
        payload["needs_guardian"] = needs_guardian_prompt(shared, request.user)
        if payload["needs_guardian"]:
            payload["name"] = ""
    return JsonResponse(payload)


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
        guardian = (getattr(shared, "guardian_name", None) or "").strip() if shared is not None else ""
        label = guardian or ((shared.name or "") if shared is not None and int(shared.herium_linked or 0) == 1 else "")
        if shared is not None and label.replace(" ", "") == name.replace(" ", ""):
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


def _shared_for_user(user):
    if not shared_enabled():
        return None
    return resolve_shared_login(user.username, user)


@ensure_csrf_cookie
def guardian_page(request):
    if not request.user.is_authenticated:
        return redirect("/login.html")
    return render(request, "guardian.html")


@require_POST
def guardian_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "로그인이 필요합니다."}, status=401)
    data = _json_body(request)
    name = (data.get("name") or "").strip()
    if len(name) < 2:
        return JsonResponse({"ok": False, "message": "보호자 성함을 입력해 주세요."}, status=400)
    user = request.user
    user.first_name = name
    user.save(update_fields=["first_name"])
    profile = _get_profile(user)
    Profile.objects.update_or_create(
        user=user,
        defaults={
            "name": name,
            "phone": profile.phone if profile else "",
            "role": profile.role if profile else Profile.ROLE_MEMBER,
            "status": profile.status if profile else Profile.STATUS_ACTIVE,
        },
    )
    shared = _shared_for_user(user)
    if shared is not None:
        set_guardian_name(shared, name)
    return JsonResponse({"ok": True, "redirect": "/main.html"})


@ensure_csrf_cookie
def account_page(request):
    if not request.user.is_authenticated:
        return redirect("/login.html")
    return render(request, "account.html")


@require_POST
def profile_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "로그인이 필요합니다."}, status=401)
    data = _json_body(request)
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    current = data.get("currentPassword") or data.get("current_password") or ""
    new_password = data.get("newPassword") or data.get("new_password") or ""
    if len(name) < 2:
        return JsonResponse({"ok": False, "message": "보호자 성함을 입력해 주세요."}, status=400)
    digits = normalize_phone(phone)
    if len(digits) < 10:
        return JsonResponse({"ok": False, "message": "올바른 휴대폰 번호를 입력해 주세요."}, status=400)
    user = request.user
    shared = _shared_for_user(user)
    if new_password:
        if len(new_password) < 4:
            return JsonResponse({"ok": False, "message": "새 비밀번호는 4자 이상이어야 합니다."}, status=400)
        ok = False
        if shared is not None:
            from .scrypt_compat import verify_password
            ok = verify_password(current, shared.password_hash)
        if not ok:
            ok = authenticate(request, username=user.username, password=current) is not None
        if not ok:
            return JsonResponse({"ok": False, "message": "현재 비밀번호가 일치하지 않습니다."}, status=400)
    if shared is not None:
        try:
            update_shared_phone(shared, digits)
            set_guardian_name(shared, name)
            if new_password:
                update_shared_password(shared, new_password)
        except SharedAuthError as exc:
            return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
    if new_password:
        user.set_password(new_password)
    user.email = email
    user.first_name = name
    user.save()
    profile = _get_profile(user)
    role = profile.role if profile else Profile.ROLE_MEMBER
    status = profile.status if profile else Profile.STATUS_ACTIVE
    profile, _created = Profile.objects.update_or_create(
        user=user,
        defaults={"name": name, "phone": format_phone_or_digits(digits), "role": role, "status": status},
    )
    cache = getattr(user._state, "fields_cache", None)
    if cache is not None:
        cache["profile"] = profile
    return JsonResponse({"ok": True, "message": "개인정보를 저장했습니다.", "user": _profile_payload(user)})


def format_phone_or_digits(digits):
    from .shared_users import format_phone
    return format_phone(digits) or digits
