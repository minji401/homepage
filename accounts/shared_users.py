from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db import IntegrityError, connections
from django.db.utils import DatabaseError

from .models import Profile, SharedUser
from .scrypt_compat import hash_password, verify_password

logger = logging.getLogger("herium.shared")


class SharedAuthError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def shared_enabled():
    return "shared" in getattr(settings, "DATABASES", {})


def shared_expected():
    return bool((os.environ.get("DATABASE_URL") or os.environ.get("SHARED_DATABASE_URL") or "").strip())


def normalize_phone(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


def format_phone(digits):
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits


def is_mobile(digits):
    return bool(digits) and digits.startswith("01") and len(digits) in (10, 11) and digits[2] in "016789"


def username_from_note(note):
    for part in (note or "").split(";"):
        item = part.strip()
        key = "herium_username="
        if item.lower().startswith(key):
            return item[len(key):].strip()
    return ""


def phone_variants(phone):
    digits = normalize_phone(phone)
    if not digits:
        return []
    values = [digits, format_phone(digits)]
    if digits.startswith("0"):
        values.append("+82" + digits[1:])
        values.append("82" + digits[1:])
    return list(dict.fromkeys(values))


def _shared_qs():
    return SharedUser.objects.using("shared")


_schema_ready = False

_USER_COLUMNS = (
    ("username", "TEXT"),
    ("email", "TEXT"),
    ("kakao_id", "TEXT"),
    ("naver_id", "TEXT"),
    ("google_id", "TEXT"),
    ("herium_linked", "INTEGER"),
    ("herium_relation", "TEXT"),
    ("herium_note", "TEXT"),
    ("guardian_name", "TEXT"),
)


def ensure_shared_schema():
    global _schema_ready
    if _schema_ready or not shared_enabled():
        return
    connection = connections["shared"]
    vendor = connection.vendor
    with connection.cursor() as cursor:
        if vendor == "sqlite":
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.fetchall()
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.fetchall()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              phone TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'user',
              herium_linked INTEGER NOT NULL DEFAULT 0,
              herium_relation TEXT,
              herium_note TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        if vendor == "sqlite":
            cursor.execute("PRAGMA table_info(users)")
            existing = {row[1] for row in cursor.fetchall()}
        else:
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                """,
                ["users"],
            )
            existing = {row[0] for row in cursor.fetchall()}
        for name, coltype in _USER_COLUMNS:
            if name in existing:
                continue
            cursor.execute(f"ALTER TABLE users ADD COLUMN {name} {coltype}")
    for row in _shared_qs().all().iterator():
        if (row.username or "").strip():
            continue
        parsed = username_from_note(row.herium_note)
        if not parsed:
            continue
        row.username = parsed
        row.save(update_fields=["username"], using="shared")
    _schema_ready = True


def get_shared_by_phone(phone):
    variants = phone_variants(phone)
    if not variants:
        return None
    try:
        ensure_shared_schema()
        return _shared_qs().filter(phone__in=variants).first()
    except DatabaseError as exc:
        logger.exception("shared users SELECT failed: %s", type(exc).__name__)
        raise SharedAuthError("회원 DB에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", 503) from exc


def get_shared_by_username(username):
    login = (username or "").strip()
    if not login:
        return None
    try:
        ensure_shared_schema()
        found = _shared_qs().filter(username__iexact=login).first()
        if found is not None:
            return found
        for row in _shared_qs().exclude(herium_note="").exclude(herium_note__isnull=True).iterator():
            parsed = username_from_note(row.herium_note)
            if parsed.lower() != login.lower():
                continue
            if not (row.username or "").strip():
                row.username = parsed
                row.save(update_fields=["username"], using="shared")
            return row
        return None
    except DatabaseError as exc:
        logger.exception("shared users SELECT failed: %s", type(exc).__name__)
        raise SharedAuthError("회원 DB에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", 503) from exc


def shared_matches_login(shared, login_id):
    login_id = (login_id or "").strip()
    if shared is None or not login_id:
        return False
    candidates = {
        (shared.username or "").strip().lower(),
        username_from_note(shared.herium_note).lower(),
        (shared.phone or "").strip(),
        normalize_phone(shared.phone),
        (shared.name or "").strip().lower(),
    }
    candidates.discard("")
    if login_id.lower() in candidates:
        return True
    digits = normalize_phone(login_id)
    return bool(digits) and digits == normalize_phone(shared.phone)


def resolve_shared_login(login_id, local=None):
    login_id = (login_id or "").strip()
    if not shared_enabled() or not login_id:
        return None
    digits = normalize_phone(login_id)
    if is_mobile(digits):
        shared = get_shared_by_phone(digits)
        if shared is not None:
            return shared
    shared = get_shared_by_username(login_id)
    if shared is not None:
        return shared
    if local is not None:
        profile = getattr(local, "profile", None)
        phone = normalize_phone(getattr(profile, "phone", "") or "")
        if phone:
            return get_shared_by_phone(phone)
    return None


def _username_hint(login_id, local, shared):
    if shared is not None and (shared.username or "").strip():
        return shared.username.strip()
    noted = username_from_note(shared.herium_note) if shared is not None else ""
    if noted:
        return noted
    if local is not None and local.username:
        return local.username
    if login_id and not is_mobile(normalize_phone(login_id)):
        return login_id.strip()
    return ""


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


def needs_guardian_prompt(shared, user=None):
    """보호자 성함은 헤리움에서 직접 입력한 값만 인정한다. 의료기 이름은 넣지 않는다."""
    del user
    if shared is None:
        return False
    buyer = (shared.name or "").strip()
    guardian = (getattr(shared, "guardian_name", None) or "").strip()
    confirmed = "guardian_confirmed=1" in (getattr(shared, "herium_note", None) or "")
    if guardian and buyer and guardian == buyer and not confirmed:
        shared.guardian_name = None
        shared.herium_linked = 0
        shared.save(update_fields=["guardian_name", "herium_linked"], using="shared")
        return True
    return not guardian


def _note_with_flag(note, flag):
    parts = [part.strip() for part in (note or "").split(";") if part.strip()]
    if flag not in parts:
        parts.append(flag)
    return ";".join(parts)


def set_guardian_name(shared, guardian_name):
    shared.guardian_name = (guardian_name or "").strip()
    shared.herium_linked = 1
    shared.herium_note = _note_with_flag(shared.herium_note, "guardian_confirmed=1")
    shared.save(update_fields=["guardian_name", "herium_linked", "herium_note"], using="shared")
    return shared


def update_shared_phone(shared, phone):
    digits = normalize_phone(phone)
    if len(digits) < 10:
        raise SharedAuthError("올바른 휴대폰 번호를 입력해 주세요.")
    other = get_shared_by_phone(digits)
    if other is not None and other.id != shared.id:
        raise SharedAuthError("이미 사용 중인 연락처입니다.")
    if shared.phone != digits:
        shared.phone = digits
        shared.save(update_fields=["phone"], using="shared")
    return shared


def mark_herium_linked(shared, note=None, username=""):
    fields = []
    if (getattr(shared, "guardian_name", None) or "").strip() and shared.herium_linked != 1:
        shared.herium_linked = 1
        fields.append("herium_linked")
    username = (username or "").strip() or username_from_note(note) or username_from_note(shared.herium_note)
    if username and not (shared.username or "").strip():
        shared.username = username
        fields.append("username")
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
    guardian = (getattr(shared, "guardian_name", None) or "").strip()
    if user is None:
        base = username if username and not User.objects.filter(username=username).exists() else shared.phone
        if User.objects.filter(username=base).exists():
            base = shared.phone
        user = User.objects.create_user(
            username=base,
            first_name=guardian,
            password=None,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    is_admin = shared.role == "admin"
    if is_admin and not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    if user.first_name != guardian:
        user.first_name = guardian
        user.save(update_fields=["first_name"])

    existing = Profile.objects.filter(user=user).first()
    profile, _created = Profile.objects.update_or_create(
        user=user,
        defaults={
            "name": guardian,
            "phone": format_phone(shared.phone) or shared.phone,
            "role": Profile.ROLE_ADMIN if is_admin else (existing.role if existing else Profile.ROLE_MEMBER),
            "status": existing.status if existing else Profile.STATUS_ACTIVE,
        },
    )
    cache = getattr(user._state, "fields_cache", None)
    if cache is not None:
        cache["profile"] = profile
    return user


def create_shared_user(*, name, phone, password, username="", relation="", as_guardian=True):
    digits = normalize_phone(phone)
    if len(digits) < 10:
        raise SharedAuthError("올바른 휴대폰 번호를 입력해 주세요.")
    ensure_shared_schema()
    if get_shared_by_phone(digits):
        raise SharedAuthError("이미 가입된 번호입니다.")
    username = (username or "").strip()
    if username and get_shared_by_username(username):
        raise SharedAuthError("이미 사용 중인 아이디입니다.")

    note = f"herium_username={username}" if username else ""
    if as_guardian:
        note = _note_with_flag(note, "guardian_confirmed=1")
    note = note or None
    buyer_name = "" if as_guardian else (name or "")
    guardian = (name or "").strip() if as_guardian else None
    shared = SharedUser(
        id=f"u_{uuid4()}",
        name=buyer_name,
        guardian_name=guardian,
        phone=digits,
        username=username or None,
        password_hash=hash_password(password),
        role="user",
        herium_linked=1 if as_guardian else 0,
        herium_relation=relation or None,
        herium_note=note,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        shared.save(using="shared", force_insert=True)
    except IntegrityError as exc:
        raise SharedAuthError("이미 가입된 번호입니다.") from exc
    except DatabaseError as exc:
        logger.exception("shared users INSERT failed: %s", type(exc).__name__)
        raise SharedAuthError("회원 DB에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", 503) from exc
    logger.info("shared users INSERT ok herium_linked=1")
    return shared


def update_shared_password(shared, password):
    shared.password_hash = hash_password(password)
    shared.save(update_fields=["password_hash"], using="shared")
    return shared


def login_with_shared(request, login_id, password):
    login_id = (login_id or "").strip()
    local = find_local_by_login(login_id)
    shared = resolve_shared_login(login_id, local)
    username_hint = _username_hint(login_id, local, shared)

    if shared is not None and verify_password(password, shared.password_hash):
        needs_guardian_prompt(shared)
        mark_herium_linked(
            shared,
            note=f"herium_username={username_hint}" if username_hint else None,
            username=username_hint,
        )
        user = sync_local_user(shared, username_hint=username_hint)
        _ensure_local_status(user)
        login(request, user)
        return user

    django_user = None
    if local is not None:
        django_user = authenticate(request, username=local.username, password=password)

    if django_user is None:
        raise SharedAuthError("아이디 또는 비밀번호가 일치하지 않습니다.")

    _ensure_local_status(django_user)
    profile = getattr(django_user, "profile", None)
    digits = normalize_phone(profile.phone if profile else "")
    if not digits:
        login(request, django_user)
        return django_user

    if shared is None or normalize_phone(shared.phone) != digits:
        shared = get_shared_by_phone(digits)

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
            update_shared_password(shared, password)
            mark_herium_linked(
                shared,
                note=f"herium_username={django_user.username}",
                username=django_user.username,
            )
    else:
        update_shared_password(shared, password)
        mark_herium_linked(
            shared,
            note=f"herium_username={django_user.username}",
            username=django_user.username,
        )

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
