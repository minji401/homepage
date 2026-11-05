import re
from datetime import datetime, timedelta, timezone

PASSWORD_RULE = "영문, 숫자, 특수문자를 포함하여 8~16자로 입력해 주세요."
PASSWORD_SPECIAL = r'[!@#$%^&*(),.?":{}|<>]'
PASSWORD_REGEX = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*' + PASSWORD_SPECIAL + r').{8,16}$'
NAME_REGEX = re.compile(r"^[가-힣A-Za-z]{2,40}$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^010\d{8}$")
LOCK_LIMIT = 5
LOCK_MINUTES = 30


def password_error(password):
    value = password or ""
    if not re.search(PASSWORD_REGEX, value):
        return PASSWORD_RULE
    return ""


def name_error(name):
    compact = re.sub(r"\s+", "", name or "")
    if not NAME_REGEX.match(compact):
        return "이름은 한글 또는 영문 2자 이상으로 입력해 주세요."
    return ""


def email_error(email):
    value = (email or "").strip()
    if not EMAIL_REGEX.match(value):
        return "이메일 형식을 확인해 주세요."
    return ""


def phone_error(digits):
    if not PHONE_REGEX.match(digits or ""):
        return "연락처는 010-0000-0000 형식으로 입력해 주세요."
    return ""


def parse_iso(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def lock_message(until):
    dt = parse_iso(until)
    if dt is None:
        return ""
    left = (dt - datetime.now(timezone.utc)).total_seconds()
    if left <= 0:
        return ""
    minutes = max(1, int((left + 59) // 60))
    return f"비밀번호를 5회 연속으로 틀려 로그인이 잠겼습니다. 약 {minutes}분 뒤에 다시 시도해 주세요."


def lock_until(now=None):
    base = now or datetime.now(timezone.utc)
    return base + timedelta(minutes=LOCK_MINUTES)
