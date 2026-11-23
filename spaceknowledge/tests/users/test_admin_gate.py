"""Unit tests for users/admin_gate.py."""

import unittest

from spaceknowledge.tests.users.fake_clock import FakeClock
from spaceknowledge.users.admin_gate import ADMIN_IDLE_TIMEOUT, ADMIN_LIFETIME, AdminGate
from spaceknowledge.users.one_time import InMemoryMailbox, OneTimePasswords
from spaceknowledge.users.session_book import SessionBook


class TestAdminGate(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock()
        self.mailbox = InMemoryMailbox()
        self.gate = AdminGate(
            OneTimePasswords(["root"], self.mailbox, clock=self.clock),
            SessionBook(clock=self.clock, lifetime=ADMIN_LIFETIME, idle_timeout=ADMIN_IDLE_TIMEOUT),
        )

    def log_in(self):
        self.gate.request_code("root")
        return self.gate.login("root", self.mailbox.messages[-1][1])

    def test_a_good_code_gives_an_admin_token(self):
        token = self.log_in()
        self.assertIsInstance(token, str)
        self.assertEqual("root", self.gate.admin_for(token))
        self.assertTrue(self.gate.logout(token))
        self.assertIsNone(self.gate.admin_for(token))

    def test_a_bad_code_gives_a_refusal(self):
        self.gate.request_code("root")
        refusal = self.gate.login("root", "00000000")
        self.assertEqual("the code is wrong, expired or already used", refusal.why)

    def test_a_player_token_is_never_an_admin_token(self):
        players = SessionBook()
        player_token = players.open("root")                # a PLAYER who happens to be called root
        self.assertIsNone(self.gate.admin_for(player_token))

    def test_an_admin_session_is_short(self):
        self.assertEqual((3600.0, 600.0), (ADMIN_LIFETIME, ADMIN_IDLE_TIMEOUT))
        token = self.log_in()
        self.clock.advance(600)                            # ten idle minutes
        self.assertIsNone(self.gate.admin_for(token))

    def test_bad_arguments_are_refused(self):
        with self.assertRaises(TypeError):
            AdminGate("codes")


if __name__ == "__main__":
    unittest.main()