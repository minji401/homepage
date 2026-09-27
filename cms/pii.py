import base64
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = "enc1:"
_DEV_KEY = b"0123456789abcdef0123456789abcdef"


def _key():
    raw = (os.environ.get("DATA_ENCRYPTION_KEY") or "").strip()
    if raw:
        try:
            key = base64.b64decode(raw)
        except Exception as exc:
            raise RuntimeError("DATA_ENCRYPTION_KEY 형식이 올바르지 않습니다.") from exc
        if len(key) != 32:
            raise RuntimeError("DATA_ENCRYPTION_KEY는 32바이트를 base64로 넣은 값이어야 합니다.")
        return key
    if os.environ.get("RENDER"):
        raise RuntimeError("RENDER 환경에는 DATA_ENCRYPTION_KEY가 필요합니다.")
    return _DEV_KEY


def encrypt_text(value):
    text = "" if value is None else str(value)
    if text == "" or text.startswith(PREFIX):
        return text
    nonce = os.urandom(12)
    sealed = AESGCM(_key()).encrypt(nonce, text.encode("utf-8"), None)
    return PREFIX + base64.b64encode(nonce + sealed).decode("ascii")


def decrypt_text(value):
    text = "" if value is None else str(value)
    if not text.startswith(PREFIX):
        return text
    blob = base64.b64decode(text[len(PREFIX):])
    nonce, sealed = blob[:12], blob[12:]
    return AESGCM(_key()).decrypt(nonce, sealed, None).decode("utf-8")


def clean_text(value, limit):
    text = str(value or "").replace("\x00", "").strip()
    if len(text) > limit:
        text = text[:limit]
    if re.search(r"<\s*/?\s*script", text, re.I):
        raise ValueError("허용되지 않는 내용입니다.")
    return text


def clean_phone(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if digits.startswith("0") and 9 <= len(digits) <= 11:
        return digits
    raise ValueError("올바른 전화번호를 입력해 주세요.")
