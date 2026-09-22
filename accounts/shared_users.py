from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.utils import OperationalError

from .models import Profile, SharedUser
from .scrypt_compat import hash_password, verify_password


class SharedAuthError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def shared_enabled():
    return "shared" in getattr(settings, "DATABASES", {})


def normalize_phone(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


def format_phone(digits):
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits


def _shared_qs():
    return SharedUser.objects.using("shared")


def get_shared_by_phone(phone):
    digits = normalize_phone(phone)
    if not digits:
        return None
    try:
        return _shared_qs().get(phone=digits)
    except SharedUser.DoesNotExist:
        return None
    except OperationalError as exc:
        raise SharedAuthError("회원 DB에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", 503) from exc


def find_local_by_phone(phone):
    digits = normalize_phone(phone)
    if not digits:
        return None
    candidates = [digits, format_phone(digits)]
    profile = Profile.objects.select_related("user").filter(phone__in=candidates).first()
    return profile.user if profile else None


def find_local_by_login(login_id):
    login_id = (login_id or "").strip()
    if not login_id:
        return None
    try:
        return User.objects.select_related("profile").get(username=login_id)
    except User.DoesNotExist:
        return find_local_by_phone(login_id)


def mark_herium_linked(shared, note=None):
    fields = []
    if shared.herium_linked != 1:
        shared.herium_linked = 1
        fields.append("herium_linked")
    if note and not shared.herium_note:
        shared.herium_note = note
        fields.append("herium_note")
    if fields:
        shared.save(update_fields=fields, using="shared")
    return shared


def sync_local_user(shared, username_hint=""):
    user = find_local_by_phone(shared.phone)
    username = (username_hint or "").strip()
    if user is None and username:
        try:
            user = User.objects.select_related("profile").get(username=username)
        except User.DoesNotExist:
            user = None
    if user is None:
        base = username if username and not User.objects.filter(username=username).exists() else shared.phone
        if User.objects.filter(username=base).exists():
            base = shared.phone
        user = User.objects.create_user(
            username=base,
            first_name=shared.name or base,
            password=None,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    is_admin = shared.role == "admin"
    if is_admin and not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    if shared.name and user.first_name != shared.name:
        user.first_name = shared.name
        user.save(update_fields=["first_name"])

    Profile.objects.update_or_create(
        user=user,
        defaults={
            "name": shared.name or user.first_name or user.username,
            "phone": format_phone(shared.phone) or shared.phone,
            "role": Profile.ROLE_ADMIN if is_admin else Profile.ROLE_MEMBER,
            "status": Profile.STATUS_ACTIVE,
        },
    )
    return user


def create_shared_user(*, name, phone, password, username="", relation=""):
    digits = normalize_phone(phone)
    if len(digits) < 10:
        raise SharedAuthError("올바른 휴대폰 번호를 입력해 주세요.")
    if get_shared_by_phone(digits):
        raise SharedAuthError("이미 가입된 번호입니다.")

    note = f"herium_username={username}" if username else None
    shared = SharedUser(
        id=f"u_{uuid4()}",
        name=name,
        phone=digits,
        password_hash=hash_password(password),
        role="user",
        herium_linked=1,
        herium_relation=relation or None,
        herium_note=note,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        shared.save(using="shared", force_insert=True)
    except IntegrityError as exc:
        raise SharedAuthError("이미 가입된 번호입니다.") from exc
    except OperationalError as exc:
        raise SharedAuthError("회원 DB에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", 503) from exc
    return shared


def update_shared_password(shared, password):
    shared.password_hash = hash_password(password)
    shared.save(update_fields=["password_hash"], using="shared")
    return shared


def login_with_shared(request, login_id, password):
    login_id = (login_id or "").strip()
    local = find_local_by_login(login_id)
    phone = normalize_phone(login_id)
    if not phone and local is not None:
        profile = getattr(local, "profile", None)
        phone = normalize_phone(profile.phone if profile else "")

    shared = get_shared_by_phone(phone) if phone else None
    username_hint = local.username if local is not None else login_id

    if shared is not None and verify_password(password, shared.password_hash):
        mark_herium_linked(shared, note=f"herium_username={username_hint}" if username_hint else None)
        user = sync_local_user(shared, username_hint=username_hint)
        _ensure_local_status(user)
        login(request, user)
        return user

    django_user = None
    if local is not None:
        django_user = authenticate(request, username=local.username, password=password)

    if django_user is None:
        if shared is not None:
            raise SharedAuthError("비밀번호가 일치하지 않습니다.")
        raise SharedAuthError("등록되지 않은 아이디 또는 휴대폰 번호입니다.")

    _ensure_local_status(django_user)
    profile = getattr(django_user, "profile", None)
    digits = normalize_phone(profile.phone if profile else "") or phone
    if not digits:
        login(request, django_user)
        return django_user

    if shared is None:
        try:
            shared = create_shared_user(
                name=(profile.name if profile else django_user.first_name) or django_user.username,
                phone=digits,
                password=password,
                username=django_user.username,
            )
        except SharedAuthError:
            shared = get_shared_by_phone(digits)
            if shared is None:
                raise
            if verify_password(password, shared.password_hash) or django_user:
                update_shared_password(shared, password)
                mark_herium_linked(shared, note=f"herium_username={django_user.username}")
    else:
        update_shared_password(shared, password)
        mark_herium_linked(shared, note=f"herium_username={django_user.username}")

    login(request, django_user)
    return django_user


def _ensure_local_status(user):
    profile = getattr(user, "profile", None)
    if profile and profile.status == Profile.STATUS_SUSPENDED:
        raise SharedAuthError("정지된 계정입니다. 관리자에게 문의해 주세요.", 403)
    if profile and profile.status == Profile.STATUS_WITHDRAWN:
        raise SharedAuthError("탈퇴 처리된 계정입니다.", 403)
    if not user.is_active:
        raise SharedAuthError("정지된 계정입니다. 관리자에게 문의해 주세요.", 403)
