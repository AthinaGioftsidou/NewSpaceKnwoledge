"""Unit tests for users/one_time.py."""

import tempfile
import unittest
from pathlib import Path

from spaceknowledge.tests.users.fake_clock import FakeClock
from spaceknowledge.users.one_time import FileMailbox, InMemoryMailbox, OneTimePasswords


class TestOneTimePasswords(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock()
        self.mailbox = InMemoryMailbox()
        self.codes = OneTimePasswords(["root"], self.mailbox, clock=self.clock,
                                      lifetime=300, max_attempts=3)

    def latest_code(self):
        return self.mailbox.messages[-1][1]

    def test_a_known_admin_gets_an_eight_digit_code(self):
        self.codes.request("root")
        recipient, code = self.mailbox.messages[0]
        self.assertEqual("root", recipient)
        self.assertEqual(8, len(code))
        self.assertTrue(code.isdecimal())

    def test_an_unknown_name_gets_nothing_and_no_error(self):
        self.codes.request("mallory")
        self.assertEqual([], self.mailbox.messages)

    def test_a_code_works_once(self):
        self.codes.request("ROOT")                         # any case: one admin
        code = self.latest_code()
        self.assertIsNone(self.codes.redeem("root", code))
        self.assertIsNotNone(self.codes.redeem("root", code))   # used up

    def test_a_code_expires(self):
        self.codes.request("root")
        self.clock.advance(300)
        self.assertIsNotNone(self.codes.redeem("root", self.latest_code()))

    def test_three_wrong_guesses_kill_the_code(self):
        self.codes.request("root")
        for _ in range(3):
            self.codes.redeem("root", "00000000")
        self.assertIsNotNone(self.codes.redeem("root", self.latest_code()))   # even the right one

    def test_a_new_request_replaces_the_old_code(self):
        self.codes.request("root")
        old = self.latest_code()
        self.codes.request("root")
        if old != self.latest_code():                      # (1 in 100 million they match)
            self.assertIsNotNone(self.codes.redeem("root", old))
        self.assertIsNone(self.codes.redeem("root", self.latest_code()))

    def test_every_failure_looks_the_same(self):
        self.codes.request("root")
        wrong = self.codes.redeem("root", "00000000")
        unknown = self.codes.redeem("mallory", "00000000")
        nothing_requested = OneTimePasswords(["root"], InMemoryMailbox()).redeem("root", "1")
        self.assertEqual(wrong.describe(), unknown.describe())
        self.assertEqual(wrong.describe(), nothing_requested.describe())

    def test_admin_names_follow_the_name_rules(self):
        with self.assertRaises(ValueError):
            OneTimePasswords(["root!"], InMemoryMailbox())


class TestFileMailbox(unittest.TestCase):

    def test_the_code_is_written_to_the_file(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "mailbox" / "admin_mailbox.txt"
        mailbox = FileMailbox(path)
        OneTimePasswords(["root"], mailbox).request("root")
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("To: root\n"))
        self.assertIn("It can be used once, within 300 seconds.", text)


if __name__ == "__main__":
    unittest.main()