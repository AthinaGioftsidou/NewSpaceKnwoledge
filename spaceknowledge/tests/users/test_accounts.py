"""Unit tests for users/account_repository.py and users/accounts.py."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.users.account_repository import (
    CorruptAccountsError, InMemoryAccountRepository, JsonAccountRepository,
)
from spaceknowledge.users.accounts import AccountRegistry

FAST = 1


class FailingRepository(InMemoryAccountRepository):
    fail = False

    def save(self, accounts):
        if self.fail:
            raise OSError("disk full")
        super().save(accounts)


class TestAccountRegistry(unittest.TestCase):

    def setUp(self):
        self.repository = FailingRepository()
        self.registry = AccountRegistry(self.repository, FAST)
        self.assertIsNone(self.registry.register("Ada", "correct horse"))

    def test_register_then_log_in(self):
        self.assertIsNone(self.registry.authenticate("ada", "correct horse"))
        self.assertIsNone(self.registry.authenticate("  ADA ", "correct horse"))   # same player
        self.assertTrue(self.registry.has_account("ADA"))
        self.assertEqual(["ada"], self.registry.names())

    def test_registration_explains_what_is_wrong(self):
        self.assertIn("3 to 20 characters", self.registry.register("al", "correct horse").why)
        self.assertIn("at least 8", self.registry.register("bob", "short").why)
        self.assertEqual("that name is already taken",
                         self.registry.register("ADA", "another password").why)

    def test_a_wrong_password_and_an_unknown_name_look_exactly_alike(self):
        wrong = self.registry.authenticate("ada", "wrong password")
        unknown = self.registry.authenticate("nobody", "wrong password")
        self.assertEqual(wrong.describe(), unknown.describe())
        self.assertEqual("the name or the password is wrong", wrong.why)

    def test_a_far_too_long_password_is_refused_without_hashing_it(self):
        self.assertIsNotNone(self.registry.authenticate("ada", "x" * 10_000))

    def test_an_account_that_cannot_be_saved_is_not_created(self):
        self.repository.fail = True
        with self.assertRaises(OSError):
            self.registry.register("bob", "another password")
        self.assertFalse(self.registry.has_account("bob"))

    def test_accounts_survive_a_restart(self):
        restarted = AccountRegistry(self.repository, FAST)
        self.assertIsNone(restarted.authenticate("ada", "correct horse"))


class TestJsonAccountRepository(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "accounts.json"

    def test_the_file_holds_salts_and_hashes_never_passwords(self):
        AccountRegistry(JsonAccountRepository(self.path), FAST).register("ada", "correct horse")
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("correct horse", text)
        self.assertEqual({"salt", "iterations", "hash"}, set(json.loads(text)["accounts"]["ada"]))
        reloaded = AccountRegistry(JsonAccountRepository(self.path), FAST)
        self.assertIsNone(reloaded.authenticate("ada", "correct horse"))

    def test_a_file_that_cannot_be_trusted_is_refused(self):
        good = {"salt": "0" * 32, "iterations": 1, "hash": "0" * 64}
        bad_files = {
            "wrong version": {"version": 2, "accounts": {}},
            "bad name":      {"version": 1, "accounts": {"Ada!": good}},
            "bad hash":      {"version": 1, "accounts": {"ada": {**good, "hash": "xyz"}}},
            "not json":      None,
        }
        for reason, document in bad_files.items():
            with self.subTest(reason=reason):
                self.path.write_text("{ broken" if document is None else json.dumps(document),
                                     encoding="utf-8")
                with self.assertRaises(CorruptAccountsError):
                    JsonAccountRepository(self.path).load()


if __name__ == "__main__":
    unittest.main()