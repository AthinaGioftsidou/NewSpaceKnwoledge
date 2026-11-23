"""Unit tests for users/credentials.py."""

import unittest

from spaceknowledge.users.credentials import (
    PasswordHash, check_password, check_username, make_hash, normalise_username,
    verify_password,
)

FAST = 1   # one hashing round: tests stay fast. The real game uses 200,000.


class TestNamesAndPasswords(unittest.TestCase):

    def test_names_are_trimmed_and_lower_cased(self):
        self.assertEqual("ada", normalise_username("  Ada "))
        with self.assertRaises(TypeError):
            normalise_username(42)

    def test_the_rules_for_a_name(self):
        self.assertIsNone(check_username("ada_99"))
        self.assertIn("3 to 20 characters", check_username("al"))
        self.assertIn("only a to z, 0 to 9 and _", check_username("ada!"))

    def test_the_rules_for_a_password(self):
        self.assertIsNone(check_password("correct horse"))
        self.assertIn("at least 8", check_password("short"))
        self.assertIn("at most 128", check_password("x" * 129))
        self.assertIsNone(check_password("       a"))   # spaces count: never trimmed


class TestHashing(unittest.TestCase):

    def test_a_hash_checks_the_right_password_only(self):
        stored = make_hash("correct horse", FAST)
        self.assertTrue(verify_password("correct horse", stored))
        self.assertFalse(verify_password("Correct horse", stored))   # exactly as chosen

    def test_the_same_password_never_gives_the_same_hash(self):
        first, second = make_hash("correct horse", FAST), make_hash("correct horse", FAST)
        self.assertNotEqual(first.salt, second.salt)
        self.assertNotEqual(first.digest, second.digest)

    def test_a_hash_holds_no_password_and_checks_its_own_shape(self):
        stored = make_hash("correct horse", FAST)
        self.assertEqual((32, 64), (len(stored.salt), len(stored.digest)))
        self.assertNotIn("correct horse", repr(stored))
        for bad in (("xyz", 1, stored.digest), (stored.salt, True, stored.digest),
                    (stored.salt, 0, stored.digest), (stored.salt, 1, "short")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    PasswordHash(*bad)


if __name__ == "__main__":
    unittest.main()