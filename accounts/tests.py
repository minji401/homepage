from django.test import SimpleTestCase

from accounts.scrypt_compat import hash_password, verify_password
from accounts.shared_users import normalize_phone


class ScryptCompatTests(SimpleTestCase):
    def test_roundtrip(self):
        stored = hash_password("hyundai-pass")
        self.assertIn(":", stored)
        self.assertTrue(verify_password("hyundai-pass", stored))
        self.assertFalse(verify_password("wrong", stored))

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("010-1234-5678"), "01012345678")
        self.assertEqual(normalize_phone("010 1234 5678"), "01012345678")
