"""현대 의료기 Node crypto.scryptSync 와 같은 saltHex:hashHex.

Node: crypto.scryptSync(password, saltHex문자열 그대로, 64)
salt는 hex decode 하지 않고 UTF-8 문자열 바이트로 넣는다.
N=16384, r=8, p=1, dklen=64
"""

from __future__ import annotations

import hashlib
import hmac
import os

SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SCRYPT_MAXMEM = 64 * 1024 * 1024
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt_hex = os.urandom(SALT_BYTES).hex()
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_hex.encode("utf-8"),
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )
    return f"{salt_hex}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or ":" not in stored:
        return False
    salt_hex, hash_hex = stored.split(":", 1)
    try:
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    actual = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_hex.encode("utf-8"),
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )
    if len(actual) != len(expected):
        return False
    return hmac.compare_digest(actual, expected)
