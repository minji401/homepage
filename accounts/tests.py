from django.test import SimpleTestCase

from accounts.scrypt_compat import hash_password, verify_password
from accounts.shared_users import (
    is_mobile,
    needs_guardian_prompt,
    normalize_phone,
    shared_matches_login,
    username_from_note,
)


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
