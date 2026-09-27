import re
from datetime import datetime, timedelta, timezone

PASSWORD_RULE = "비밀번호는 8자 이상이며 영문 대문자, 소문자, 숫자, 특수문자를 각각 하나 이상 포함해야 합니다."
LOCK_LIMIT = 5
LOCK_MINUTES = 30


def password_error(password):
    value = password or ""
    if (
        len(value) < 8
        or not re.search(r"[a-z]", value)
        or not re.search(r"[A-Z]", value)
        or not re.search(r"\d", value)
        or not re.search(r"[^A-Za-z0-9]", value)
    ):
        return PASSWORD_RULE
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
