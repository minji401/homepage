from django.test import SimpleTestCase

from accounts.scrypt_compat import hash_password, verify_password
from accounts.shared_users import (
    is_mobile,
    needs_guardian_prompt,
    normalize_phone,
    shared_matches_login,
    username_from_note,
)


class PasswordPolicyTests(SimpleTestCase):
    def test_rejects_short_or_simple_passwords(self):
        from accounts.password_policy import password_error

        self.assertTrue(password_error("short1A"))
        self.assertTrue(password_error("lowercase1!"))
        self.assertTrue(password_error("UPPERCASE1!"))
        self.assertTrue(password_error("NoDigits!!"))
        self.assertTrue(password_error("NoSpecial1A"))
        self.assertEqual(password_error("GoodPass1!"), "")

    def test_names_match_ignores_spaces(self):
        from accounts.shared_users import names_match

        self.assertTrue(names_match("홍 길동", "홍길동"))
        self.assertFalse(names_match("홍길동", "김보호"))

    def test_lock_message_mentions_remaining_minutes(self):
        from datetime import timedelta

        from accounts.password_policy import lock_message, lock_until

        self.assertIn("분", lock_message(lock_until()))
        self.assertEqual(lock_message(lock_until() - timedelta(minutes=40)), "")


class LoginThrottleTests(SimpleTestCase):
    def test_blocks_after_eight_failures(self):
        from accounts.views import _clear_login_fail, _login_blocked, _note_login_fail

        ip = "test-login-throttle"
        _clear_login_fail(ip)
        self.assertFalse(_login_blocked(ip))
        for _ in range(8):
            _note_login_fail(ip)
        self.assertTrue(_login_blocked(ip))
        _clear_login_fail(ip)
        self.assertFalse(_login_blocked(ip))


class ScryptCompatTests(SimpleTestCase):
    def test_roundtrip(self):
        stored = hash_password("hyundai-pass")
        salt_hex, hash_hex = stored.split(":", 1)
        self.assertTrue(all(c in "0123456789abcdef" for c in salt_hex))
        self.assertTrue(verify_password("hyundai-pass", stored))
        self.assertFalse(verify_password("wrong", stored))

    def test_uses_salt_hex_string_not_unhexed_bytes(self):
        import hashlib

        from accounts.scrypt_compat import SCRYPT_DKLEN, SCRYPT_MAXMEM, SCRYPT_N, SCRYPT_P, SCRYPT_R

        stored = hash_password("secret")
        salt_hex, hash_hex = stored.split(":", 1)
        as_string = hashlib.scrypt(
            b"secret",
            salt=salt_hex.encode("utf-8"),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=SCRYPT_DKLEN,
            maxmem=SCRYPT_MAXMEM,
        ).hex()
        as_unhexed = hashlib.scrypt(
            b"secret",
            salt=bytes.fromhex(salt_hex),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=SCRYPT_DKLEN,
            maxmem=SCRYPT_MAXMEM,
        ).hex()
        self.assertEqual(hash_hex, as_string)
        self.assertNotEqual(hash_hex, as_unhexed)

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("010-1234-5678"), "01012345678")
        self.assertEqual(normalize_phone("010 1234 5678"), "01012345678")

    def test_is_mobile_ignores_digits_inside_username(self):
        self.assertTrue(is_mobile("01012345678"))
        self.assertFalse(is_mobile("1234"))
        self.assertFalse(is_mobile(normalize_phone("user1234")))

    def test_username_from_note(self):
        self.assertEqual(username_from_note("herium_username=hatsal;password_reset_required=1"), "hatsal")
        self.assertEqual(username_from_note(""), "")

    def test_shared_matches_login_by_note_username(self):
        shared = type("Shared", (), {})()
        shared.username = ""
        shared.phone = "01012345678"
        shared.name = "홍길동"
        shared.herium_note = "herium_username=hatsal"
        self.assertTrue(shared_matches_login(shared, "hatsal"))
        self.assertTrue(shared_matches_login(shared, "010-1234-5678"))
        self.assertFalse(shared_matches_login(shared, "other"))

    def test_copied_buyer_name_is_not_a_guardian_name(self):
        shared = type("Shared", (), {})()
        shared.name = "김구매"
        shared.guardian_name = "김구매"
        shared.herium_linked = 1
        shared.herium_note = "herium_username=buyer1"
        shared.save = lambda **_kwargs: None
        self.assertTrue(needs_guardian_prompt(shared))
        self.assertIsNone(shared.guardian_name)
        self.assertEqual(shared.herium_linked, 0)

    def test_confirmed_guardian_keeps_the_same_name_as_the_buyer(self):
        shared = type("Shared", (), {})()
        shared.name = "김구매"
        shared.guardian_name = "김구매"
        shared.herium_linked = 1
        shared.herium_note = "herium_username=buyer1;guardian_confirmed=1"
        shared.save = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not clear"))
        self.assertFalse(needs_guardian_prompt(shared))
        self.assertEqual(shared.guardian_name, "김구매")


class StagingGateTests(SimpleTestCase):
    def test_signup_is_blocked_when_registration_is_closed(self):
        import os
        from unittest.mock import patch

        from django.test import RequestFactory

        from accounts.views import signup_api

        request = RequestFactory().post(
            "/accounts/signup/",
            data=b"{}",
            content_type="application/json",
        )
        with patch.dict(os.environ, {"ALLOW_REGISTRATION": "false"}):
            response = signup_api(request)
        self.assertEqual(response.status_code, 403)

    def test_basic_auth_blocks_until_the_password_matches(self):
        import base64
        import os
        from unittest.mock import patch

        from django.http import HttpResponse
        from django.test import RequestFactory

        from herium.middleware import StagingAuthMiddleware

        middleware = StagingAuthMiddleware(lambda _request: HttpResponse("ok"))
        request = RequestFactory().get("/main.html")
        with patch.dict(os.environ, {"STAGING_USER": "tester", "STAGING_PASSWORD": "secret"}):
            blocked = middleware(request)
            self.assertEqual(blocked.status_code, 401)
            request.META["HTTP_AUTHORIZATION"] = "Basic " + base64.b64encode(b"tester:secret").decode()
            opened = middleware(request)
        self.assertEqual(opened.status_code, 200)
