"""Unit tests for client/game_client.py, against a real broker web server."""

import unittest

from spaceknowledge.client.game_client import GameClient, SessionEnded
from spaceknowledge.common.refusal import Refusal
from spaceknowledge.tests.app.helpers import PASSWORD
from spaceknowledge.tests.broker_web.web_helpers import a_broker_web


class TestGameClient(unittest.TestCase):

    def setUp(self):
        web, _, _ = a_broker_web(self)
        self.client = GameClient(*web.address)

    def logged_in(self, name):
        self.assertIsNone(self.client.register(name, PASSWORD))
        return self.client.login(name, PASSWORD)

    def test_register_log_in_play_log_out(self):
        token = self.logged_in("ada")
        self.assertEqual("You are at Earth.", self.client.command(token, "where"))
        self.assertTrue(self.client.logout(token))
        with self.assertRaises(SessionEnded):
            self.client.command(token, "where")

    def test_a_refusal_is_an_answer_not_an_exception(self):
        self.assertIsInstance(self.client.login("nobody", PASSWORD), Refusal)
        token = self.logged_in("ada")
        self.assertTrue(self.client.command(token, "dance").startswith("Refused: dance."))

    def test_news_comes_with_the_number_to_ask_from_next(self):
        ada, bob = self.logged_in("ada"), self.logged_in("bob")
        _, latest = self.client.news(bob, 0)
        self.client.command(ada, "drop torch")
        texts, newer = self.client.news(bob, latest)
        self.assertEqual(["ada dropped a torch"], texts)
        self.assertEqual(([], newer), self.client.news(bob, newer))     # nothing new since

    def test_nothing_is_sent_for_a_bad_number(self):
        with self.assertRaises(ValueError):
            self.client.news("token", -1)


if __name__ == "__main__":
    unittest.main()