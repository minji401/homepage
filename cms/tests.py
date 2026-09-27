from django.test import SimpleTestCase

from cms.pii import clean_phone, clean_text, decrypt_text, encrypt_text


class PiiTests(SimpleTestCase):
    def test_roundtrip(self):
        sealed = encrypt_text("홍길동")
        self.assertTrue(sealed.startswith("enc1:"))
        self.assertNotIn("홍길동", sealed)
        self.assertEqual(decrypt_text(sealed), "홍길동")

    def test_plaintext_still_reads(self):
        self.assertEqual(decrypt_text("기존 이름"), "기존 이름")

    def test_script_rejected(self):
        with self.assertRaises(ValueError):
            clean_text("<script>alert(1)</script>", 200)

    def test_phone(self):
        self.assertEqual(clean_phone("01012345678"), "010-1234-5678")
        self.assertEqual(clean_phone("054-334-9986"), "0543349986")
