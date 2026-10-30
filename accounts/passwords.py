"""scrypt(기존 회원)과 bcrypt(신규 해시)를 함께 검증합니다."""

from __future__ import annotations

import hmac
import os

from .scrypt_compat import hash_password as hash_scrypt
from .scrypt_compat import verify_password as verify_scrypt

try:
    import bcrypt as _bcrypt
except Exception:
    _bcrypt = None


def _is_bcrypt(stored: str) -> bool:
    value = stored or ""
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")


def hash_password(password: str) -> str:
    if _bcrypt is None:
        return hash_scrypt(password)
    digest = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt(rounds=12))
    return digest.decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    if stored == "!":
        return False
    if _is_bcrypt(stored):
        if _bcrypt is None:
            return False
        try:
            return _bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
        except Exception:
            return False
    return verify_scrypt(password, stored)


def needs_rehash(stored: str) -> bool:
    return bool(stored) and not _is_bcrypt(stored) and _bcrypt is not None


def dummy_compare(password: str) -> None:
    """타이밍 비교용. 결과는 쓰지 않습니다."""
    if _bcrypt is not None:
        _bcrypt.checkpw(password.encode("utf-8"), b"$2b$12$abcdefghijklmnopqrstuvabcdefghijklmnopqrstuvabcdefe")
        return
    hmac.compare_digest(os.urandom(16), os.urandom(16))
