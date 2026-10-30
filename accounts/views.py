import json
import logging
import time

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from herium.middleware import registration_open
from .models import Profile
from .password_policy import PASSWORD_RULE, password_error, lock_message, lock_until
from .jwt_auth import issue_token
from .passwords import verify_password
from .shared_users import (
    SharedAuthError,
    clear_login_failure,
    create_shared_user,
    find_local_by_login,
    format_phone,
    get_shared_by_email,
    get_shared_by_phone,
    is_mobile,
    issue_reset_token,
    login_with_shared,
    member_without_email,
    needs_guardian_prompt,
    normalize_phone,
    open_password_help,
    resolve_shared_login,
    set_guardian_name,
    shared_enabled,
    shared_expected,
    take_reset_token,
    update_shared_password,
    update_shared_phone,
    username_from_note,
    withdraw_shared_user,
)


logger = logging.getLogger("herium")

_LOGIN_WINDOW = 10 * 60
_LOGIN_MAX = 8
_login_fails = {}


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.META.get("REMOTE_ADDR") or "unknown"


def _note_login_fail(ip):
    now = time.time()
    row = _login_fails.get(ip)
    if not row or now - row["t"] > _LOGIN_WINDOW:
        _login_fails[ip] = {"n": 1, "t": now}
    else:
        row["n"] += 1
    if len(_login_fails) > 5000:
        cutoff = now - _LOGIN_WINDOW
        for key in list(_login_fails):
            if _login_fails[key]["t"] < cutoff:
                del _login_fails[key]


def _login_blocked(ip):
    row = _login_fails.get(ip)
    if not row or time.time() - row["t"] > _LOGIN_WINDOW:
        return False
    return row["n"] >= _LOGIN_MAX


def _clear_login_fail(ip):
    _login_fails.pop(ip, None)


_reset_hits = {}


def _note_reset(ip):
    now = time.time()
    row = _reset_hits.get(ip)
    if not row or now - row["t"] > _LOGIN_WINDOW:
        _reset_hits[ip] = {"n": 1, "t": now}
    else:
        row["n"] += 1


def _reset_blocked(ip):
    row = _reset_hits.get(ip)
    if not row or time.time() - row["t"] > _LOGIN_WINDOW:
        return False
    return row["n"] > 8


_help_hits = {}


def _note_help(ip):
    now = time.time()
    row = _help_hits.get(ip)
    if not row or now - row["t"] > _LOGIN_WINDOW:
        _help_hits[ip] = {"n": 1, "t": now}
    else:
        row["n"] += 1


def _help_blocked(ip):
    row = _help_hits.get(ip)
    if not row or time.time() - row["t"] > _LOGIN_WINDOW:
        return False
    return row["n"] > 8


def _profile_locked(profile):
    if profile is None or not profile.login_locked_until:
        return ""
    message = lock_message(profile.login_locked_until)
    if message:
        return message
    profile.login_failures = 0
    profile.login_locked_until = None
    profile.save(update_fields=["login_failures", "login_locked_until"])
    return ""


def _note_profile_failure(profile):
    if profile is None:
        return ""
    count = int(profile.login_failures or 0) + 1
    if count >= 5:
        until = lock_until()
        profile.login_failures = count
        profile.login_locked_until = until
        profile.save(update_fields=["login_failures", "login_locked_until"])
        return lock_message(until)
    profile.login_failures = count
    profile.save(update_fields=["login_failures"])
    return ""


def _clear_profile_failure(profile):
    if profile is None:
        return
    if not profile.login_failures and not profile.login_locked_until:
        return
    profile.login_failures = 0
    profile.login_locked_until = None
    profile.save(update_fields=["login_failures", "login_locked_until"])


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
    shared = None
    if shared_enabled():
        shared = resolve_shared_login(user.username, user)
    return {
        "authenticated": True,
        "id": user.username,
        "user_id": shared.id if shared is not None else str(user.pk),
        "token": issue_token(
            shared.id if shared is not None else str(user.pk),
            "ADMIN" if is_admin else "USER",
        ),
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

    ip = _client_ip(request)
    if _login_blocked(ip):
        return JsonResponse(
            {"ok": False, "message": "로그인 시도가 너무 많습니다. 10분 뒤에 다시 시도해 주세요."},
            status=429,
        )

    if shared_expected() and not shared_enabled():
        return JsonResponse(
            {"ok": False, "message": "공유 회원 DB가 연결되지 않았습니다. Render DATABASE_URL을 확인해 주세요."},
            status=503,
        )
    if shared_enabled():
        try:
            user = login_with_shared(request, user_id, password)
        except SharedAuthError as exc:
            if exc.status in (400, 423):
                _note_login_fail(ip)
            return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
        _clear_login_fail(ip)
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
            _note_login_fail(ip)
            return JsonResponse({"ok": False, "message": "아이디 또는 비밀번호가 일치하지 않습니다."}, status=400)
    except OperationalError:
        return JsonResponse({"ok": False, "message": "회원 DB가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요."}, status=503)

    profile = _get_profile(existing)
    locked = _profile_locked(profile)
    if locked:
        _note_login_fail(ip)
        return JsonResponse({"ok": False, "message": locked}, status=423)
    user = authenticate(request, username=existing.username, password=password)
    if user is None:
        _note_login_fail(ip)
        locked = _note_profile_failure(profile)
        if locked:
            return JsonResponse({"ok": False, "message": locked}, status=423)
        return JsonResponse({"ok": False, "message": "아이디 또는 비밀번호가 일치하지 않습니다."}, status=400)
    if profile and profile.status == Profile.STATUS_SUSPENDED:
        return JsonResponse({"ok": False, "message": "정지된 계정입니다. 관리자에게 문의해 주세요."}, status=403)
    if profile and profile.status == Profile.STATUS_WITHDRAWN:
        return JsonResponse({"ok": False, "message": "탈퇴 처리된 계정입니다."}, status=403)
    if not user.is_active:
        return JsonResponse({"ok": False, "message": "정지된 계정입니다. 관리자에게 문의해 주세요."}, status=403)

    _clear_login_fail(ip)
    _clear_profile_failure(profile)
    login(request, user)
    payload = _profile_payload(user)
    return JsonResponse({"ok": True, "user": payload, "redirect": "/staff/" if payload["is_admin"] else "/main.html"})


@ensure_csrf_cookie
def signup_page(request):
    if request.user.is_authenticated:
        return redirect("/main.html")
    return render(request, "signup.html", {"registration_open": registration_open()})


@require_GET
def public_config(request):
    return JsonResponse({"registrationOpen": registration_open()})


@csrf_exempt
@require_POST
def signup_api(request):
    if not registration_open():
        return JsonResponse({"ok": False, "message": "현재 정식 오픈 준비 중입니다."}, status=403)
    data = _json_body(request)
    user_id = (data.get("id") or "").strip()
    password = data.get("password") or ""
    password_confirm = data.get("passwordConfirm") or data.get("password_confirm") or ""
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    agree = data.get("agree") in (True, "true", "on", "1", 1)
    age14 = data.get("age14") in (True, "true", "on", "1", 1)
    marketing = data.get("marketing") in (True, "true", "on", "1", 1)

    if not user_id or not password or not name or not phone:
        return JsonResponse({"ok": False, "message": "아이디, 비밀번호, 이름, 연락처는 필수입니다."}, status=400)
    if len(user_id) < 4:
        return JsonResponse({"ok": False, "message": "아이디는 4자 이상 입력해 주세요."}, status=400)
    if password_error(password):
        return JsonResponse({"ok": False, "message": PASSWORD_RULE}, status=400)
    if password_confirm and password != password_confirm:
        return JsonResponse({"ok": False, "message": "비밀번호가 서로 다릅니다."}, status=400)
    if not agree:
        return JsonResponse({"ok": False, "message": "이용약관 및 개인정보 처리에 동의해 주세요."}, status=400)
    if not age14:
        return JsonResponse({"ok": False, "message": "만 14세 이상만 가입할 수 있습니다."}, status=400)
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
            create_shared_user(
                name=name,
                phone=digits,
                password=password,
                username=user_id,
                email=email,
                age_14=True,
                marketing=marketing,
            )
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
        return JsonResponse(
            {
                "ok": False,
                "message": "비밀번호는 이 화면에서 바꾸지 않습니다. 헤리움 케어센터 054-334-9986으로 전화해 주세요.",
            },
            status=403,
        )

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
        if password_error(new_password):
            return JsonResponse({"ok": False, "message": PASSWORD_RULE}, status=400)
        ok = False
        if shared is not None:
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
            if email:
                taken = get_shared_by_email(email)
                if taken is not None and taken.id != shared.id:
                    return JsonResponse({"ok": False, "message": "이미 사용 중인 이메일입니다."}, status=400)
                shared.email = email
                shared.save(update_fields=["email"], using="shared")
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


@csrf_exempt
@require_POST
def withdraw_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "로그인이 필요합니다."}, status=401)
    user = request.user
    shared = _shared_for_user(user)
    if shared is not None:
        withdraw_shared_user(shared)
    profile = _get_profile(user)
    if profile:
        profile.name = "탈퇴회원"
        profile.phone = ""
        profile.status = Profile.STATUS_WITHDRAWN
        profile.save(update_fields=["name", "phone", "status"])
    user.first_name = "탈퇴회원"
    user.is_active = False
    user.set_unusable_password()
    user.save()
    logout(request)
    return JsonResponse({"ok": True, "message": "탈퇴가 완료되었습니다. 주문·결제 기록은 관계 법령에 따라 보관됩니다."})


def format_phone_or_digits(digits):
    from .shared_users import format_phone
    return format_phone(digits) or digits


RESET_SENT = "가입된 이메일이라면 재설정 링크를 보냈습니다. 30분 안에 메일을 확인해 주세요."
HELP_SENT = "요청을 접수했습니다. 고객센터(054-334-9986)에서 본인 확인 후 연락드립니다."


def _valid_email(value):
    text = (value or "").strip()
    return "@" in text and "." in text.split("@")[-1] and " " not in text


def mail_configured():
    return bool(getattr(settings, "EMAIL_HOST", "") and getattr(settings, "EMAIL_HOST_USER", ""))


@csrf_exempt
@require_POST
def password_reset_request(request):
    ip = _client_ip(request)
    _note_reset(ip)
    if _reset_blocked(ip):
        return JsonResponse({"ok": False, "message": "요청이 너무 많습니다. 10분 뒤에 다시 시도해 주세요."}, status=429)
    data = _json_body(request)
    email = (data.get("email") or "").strip()
    if not _valid_email(email):
        return JsonResponse({"ok": False, "message": "이메일 형식을 확인해 주세요."}, status=400)
    if not mail_configured():
        return JsonResponse(
            {"ok": False, "message": "비밀번호 재설정 메일을 보낼 설정이 아직 없습니다. 관리자에게 문의해 주세요."},
            status=503,
        )
    if not shared_enabled():
        return JsonResponse({"ok": False, "message": "회원 DB가 아직 준비되지 않았습니다."}, status=503)
    try:
        shared = get_shared_by_email(email)
    except SharedAuthError as exc:
        return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
    if shared is not None:
        token = issue_reset_token(shared.id)
        link = settings.SITE_URL + "/reset-password.html?token=" + token
        try:
            send_mail(
                "헤리움 케어센터 비밀번호 재설정",
                "아래 주소에서 새 비밀번호를 정해 주세요. 이 링크는 30분 뒤에 만료됩니다.\n\n"
                + link
                + "\n\n본인이 요청하지 않았다면 이 메일을 무시하세요.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("password reset mail failed")
    return JsonResponse({"ok": True, "message": RESET_SENT})


@require_POST
def password_help_request(request):
    ip = _client_ip(request)
    _note_help(ip)
    if _help_blocked(ip):
        return JsonResponse({"ok": False, "message": "요청이 너무 많습니다. 10분 뒤에 다시 시도해 주세요."}, status=429)
    data = _json_body(request)
    name = (data.get("name") or "").strip()
    digits = normalize_phone(data.get("phone") or "")
    if len(name) < 2 or not is_mobile(digits):
        return JsonResponse({"ok": False, "message": "이름과 휴대폰 번호를 확인해 주세요."}, status=400)
    if shared_enabled():
        try:
            shared = member_without_email(name, digits)
            if shared is not None:
                open_password_help(shared.id, name, format_phone(digits) or digits, "herium")
        except SharedAuthError:
            logger.exception("password help lookup failed")
            return JsonResponse(
                {"ok": False, "message": "지금은 요청을 저장할 수 없습니다. 054-334-9986으로 전화해 주세요."},
                status=503,
            )
        except Exception:
            logger.exception("password help request failed")
            return JsonResponse(
                {"ok": False, "message": "지금은 요청을 저장할 수 없습니다. 054-334-9986으로 전화해 주세요."},
                status=503,
            )
    return JsonResponse({"ok": True, "message": HELP_SENT})


@csrf_exempt
@require_POST
def password_reset_confirm(request):
    data = _json_body(request)
    token = (data.get("token") or "").strip()
    password = data.get("password") or ""
    if not token:
        return JsonResponse({"ok": False, "message": "재설정 링크가 올바르지 않습니다."}, status=400)
    if password_error(password):
        return JsonResponse({"ok": False, "message": PASSWORD_RULE}, status=400)
    if not shared_enabled():
        return JsonResponse({"ok": False, "message": "회원 DB가 아직 준비되지 않았습니다."}, status=503)
    user_id = take_reset_token(token)
    if not user_id:
        return JsonResponse(
            {"ok": False, "message": "재설정 링크가 없거나 만료되었습니다. 비밀번호 찾기에서 다시 요청해 주세요."},
            status=400,
        )
    from .models import SharedUser
    shared = SharedUser.objects.using("shared").filter(id=user_id).first()
    if shared is None:
        return JsonResponse(
            {"ok": False, "message": "재설정 링크가 없거나 만료되었습니다. 비밀번호 찾기에서 다시 요청해 주세요."},
            status=400,
        )
    update_shared_password(shared, password)
    clear_login_failure(shared)
    local = find_local_by_login((shared.username or "").strip() or shared.phone)
    if local is not None:
        local.set_password(password)
        local.save(update_fields=["password"])
    return JsonResponse({"ok": True, "message": "비밀번호를 바꿨습니다. 다시 로그인해 주세요."})


def reset_page(request):
    return render(request, "reset-password.html")
