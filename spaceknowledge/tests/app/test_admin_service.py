"""Unit tests for app/admin_service.py: what an administrator may do."""

import unittest

from spaceknowledge.common.refusal import Refusal
from spaceknowledge.tests.app.helpers import PASSWORD, a_game


class TestAdminService(unittest.TestCase):

    def setUp(self):
        self.front, self.admin, self.mailbox = a_game(self)
        self.front.register("bob", PASSWORD)
        self.front.register("ada", PASSWORD)

    def admin_token(self):
        self.admin.request_code("root")
        return self.admin.login("root", self.mailbox.messages[-1][1])

    def test_an_admin_sees_the_players_and_the_numbers(self):
        token = self.admin_token()
        self.assertEqual(["ada", "bob"], self.admin.players(token))
        stats = self.admin.stats(token)
        self.assertEqual("broker-1", stats["broker"])
        self.assertEqual(2, stats["registered_players"])
        self.assertTrue(stats["broker_thread_running"])

    def test_without_an_admin_token_nothing_is_shown(self):
        player_token = self.front.login("ada", PASSWORD)
        for token in ("made-up", player_token):
            with self.subTest(token=token):
                self.assertIsInstance(self.admin.players(token), Refusal)
                self.assertIsInstance(self.admin.stats(token), Refusal)

    def test_an_admin_cannot_play(self):
        self.assertIsInstance(self.front.command(self.admin_token(), "where"), Refusal)


if __name__ == "__main__":
    unittest.main()