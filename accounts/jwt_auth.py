from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from django.conf import settings


def _secret():
    return (os.environ.get("JWT_SECRET") or getattr(settings, "SECRET_KEY", "") or "dev-jwt").encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + pad)


def issue_token(user_id: str, role: str = "user", hours: int = 24 * 14) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    now = int(time.time())
    payload = _b64(
        json.dumps(
            {"sub": str(user_id), "role": role or "user", "iat": now, "exp": now + hours * 3600},
            separators=(",", ":"),
        ).encode("utf-8")
    )
    sig = hmac.new(_secret(), f"{header}.{payload}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(sig)}"


def read_token(token: str):
    if not token or token.count(".") != 2:
        return None
    header, payload, sig = token.split(".")
    expect = hmac.new(_secret(), f"{header}.{payload}".encode("ascii"), hashlib.sha256).digest()
    given = _unb64(sig)
    if len(expect) != len(given) or not hmac.compare_digest(expect, given):
        return None
    try:
        data = json.loads(_unb64(payload).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if int(data.get("exp") or 0) < int(time.time()):
        return None
    return data


def bearer_user_id(request):
    header = request.META.get("HTTP_AUTHORIZATION") or ""
    if header.lower().startswith("bearer "):
        data = read_token(header[7:].strip())
        if data:
            return data.get("sub")
    return None
