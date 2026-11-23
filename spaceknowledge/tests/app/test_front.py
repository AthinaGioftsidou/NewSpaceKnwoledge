"""Unit tests for app/front.py: the door every player comes through."""

import unittest

from spaceknowledge.common.refusal import Refusal
from spaceknowledge.tests.app.helpers import PASSWORD, a_game


class TestFront(unittest.TestCase):

    def setUp(self):
        self.front, _, _ = a_game(self)
        self.front.register("ada", PASSWORD)

    def test_log_in_then_play(self):
        token = self.front.login("ada", PASSWORD)
        self.assertIsInstance(token, str)
        self.assertEqual("You are at Earth.", self.front.command(token, "where"))
        self.assertEqual("You are carrying: torch", self.front.command(token, "inventory"))

    def test_a_wrong_password_gets_no_token(self):
        self.assertIsInstance(self.front.login("ada", "wrong password"), Refusal)

    def test_after_five_wrong_passwords_even_the_right_one_waits(self):
        for _ in range(5):
            self.front.login("ada", "wrong password")
        refusal = self.front.login("ada", PASSWORD)
        self.assertIn("logging in is paused", refusal.why)

    def test_no_token_means_no_game(self):
        refusal = self.front.command("made-up-token", "where")
        self.assertEqual("you are not logged in", refusal.why)

    def test_the_token_decides_who_you_are(self):
        self.front.register("bob", PASSWORD)
        ada, bob = self.front.login("ada", PASSWORD), self.front.login("bob", PASSWORD)
        self.front.command(ada, "mine iron 5")
        self.assertEqual("You are carrying: torch\nResources: iron 5", self.front.command(ada, "i"))
        self.assertEqual("You are carrying: torch", self.front.command(bob, "i"))

    def test_logging_out_ends_the_token(self):
        token = self.front.login("ada", PASSWORD)
        self.assertTrue(self.front.logout(token))
        self.assertTrue(self.front.submit(token, "where").startswith("Refused: send a command"))


if __name__ == "__main__":
    unittest.main()