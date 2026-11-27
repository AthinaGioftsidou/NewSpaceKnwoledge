"""Unit tests for client/console.py: the terminal menu and game, with typed
lines given in a list instead of a keyboard."""

import unittest

from spaceknowledge.client.console import run_client
from spaceknowledge.client.game_client import GameClient
from spaceknowledge.tests.app.helpers import PASSWORD
from spaceknowledge.tests.broker_web.web_helpers import a_broker_web


def typing(*lines):
    """A pretend keyboard: each call gives the next line, then the input ends."""
    queue = list(lines)

    def read(prompt=""):
        if not queue:
            raise EOFError
        return queue.pop(0)
    return read


class TestConsole(unittest.TestCase):

    def setUp(self):
        web, self.front, _ = a_broker_web(self)
        self.client = GameClient(*web.address)
        self.shown = []

    def play(self, *lines):
        keys = typing(*lines)
        run_client(self.client, keys, keys, self.shown.append)

    def test_register_then_log_in_and_play(self):
        self.play("register", "ada", PASSWORD, "login", "ada", PASSWORD, "where", "quit")
        self.assertIn("Account created. Now type login.", self.shown)
        self.assertIn("You are at Earth.", self.shown)
        self.assertEqual("Goodbye.", self.shown[-1])

    def test_what_another_player_does_is_shown_after_your_command(self):
        self.front.register("ada", PASSWORD)
        self.front.register("bob", PASSWORD)
        ada = self.front.login("ada", PASSWORD)
        keys = typing("login", "bob", PASSWORD, "where", "quit")

        def read(prompt=""):
            line = keys(prompt)
            if line == "where":
                self.front.command(ada, "drop torch")      # ada drops while bob is playing
            return line
        run_client(self.client, read, read, self.shown.append)
        self.assertIn("  * ada dropped a torch", self.shown)

    def test_an_unknown_menu_choice_is_explained(self):
        self.play("dance")
        self.assertTrue(self.shown[-1].startswith("Refused: dance."))


if __name__ == "__main__":
    unittest.main()