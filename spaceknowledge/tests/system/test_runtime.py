"""AUTOMATED RUNTIME TESTS: the real programs, running, driven by the real clients.

Nothing is faked here. A Universe and two Brokers start on real TCP ports
(port 0: the system picks free ones, so a running game is never disturbed),
in a temporary state folder (never the real one). The players use GameClient
and the administrator uses AdminClient, the same classes the terminal
programs use, over HTTP. The test then plays the game and checks the
answers, the pop-up news, the admin's view, and a restart.
"""

import re
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.app.broker_program import start_broker_node
from spaceknowledge.app.layout import WORLD_FILE
from spaceknowledge.app.paths import MAILBOX_FILE
from spaceknowledge.app.universe_program import start_universe
from spaceknowledge.client.admin_client import AdminClient
from spaceknowledge.client.game_client import GameClient
from spaceknowledge.tests.app.helpers import PASSWORD

BROKERS = ("broker-1", "broker-2")


class TestRuntime(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.state = Path(folder.name)
        self.universe = self.start_universe()

    def start_universe(self):
        universe = start_universe(WORLD_FILE, self.state / "universe", port=0, peers=BROKERS)
        self.addCleanup(universe.close)
        return universe

    def start_broker(self, name):
        host, port = self.universe.address
        node = start_broker_node(self.state / name, self.state / "universe" / "server.key",
                                 host, port, "earth", name, web_port=0, iterations=1)
        self.addCleanup(node.close)
        return node

    def player(self, node, name):
        """A real client, registered and logged in. Returns (client, token)."""
        client = GameClient(*node.address)
        self.assertIsNone(client.register(name, PASSWORD))
        token = client.login(name, PASSWORD)
        self.assertIsInstance(token, str)
        return client, token

    def test_two_players_on_two_brokers_play_together(self):
        ada, ada_token = self.player(self.start_broker("broker-1"), "ada")
        bob, bob_token = self.player(self.start_broker("broker-2"), "bob")
        _, seen = bob.news(bob_token, 0)
        self.assertEqual("You drop the torch.", ada.command(ada_token, "drop torch"))
        texts, seen = bob.news(bob_token, seen)
        self.assertEqual(["ada dropped a torch"], texts)            # the pop-up, across Brokers
        self.assertIn("torch", bob.command(bob_token, "look"))
        self.assertEqual("You pick up the torch.", bob.command(bob_token, "pick torch"))
        texts, _ = ada.news(ada_token, 0)
        self.assertIn("bob picked up a torch", texts)
        self.assertEqual("You are carrying: torch, torch", bob.command(bob_token, "inventory"))

    def test_the_admin_logs_in_with_the_mailbox_code_and_sees_the_numbers(self):
        node = self.start_broker("broker-1")
        ada, token = self.player(node, "ada")
        ada.command(token, "mine iron 3")
        admin = AdminClient(*node.address)
        self.assertIsNone(admin.request_code("root"))
        mail = (self.state / "broker-1" / MAILBOX_FILE).read_text(encoding="utf-8")
        code = re.search(r"Code: (\d{8})", mail).group(1)
        admin_token = admin.login("root", code)
        self.assertEqual(["ada"], admin.players(admin_token))
        stats = admin.stats(admin_token)
        self.assertGreaterEqual(stats["requests_served"], 2)        # the join and the mining
        self.assertEqual(0, stats["queue_depth"])

    def test_everything_survives_a_restart_of_both_programs(self):
        node = self.start_broker("broker-1")
        ada, token = self.player(node, "ada")
        ada.command(token, "mine iron 20")
        ada.command(token, "answer rust")                           # opens the way to Mars
        node.close()
        self.universe.close()
        self.universe = self.start_universe()                       # the same state folder
        node = self.start_broker("broker-1")
        ada = GameClient(*node.address)
        token = ada.login("ada", PASSWORD)                          # the account is still there
        self.assertIn("iron 20", ada.command(token, "inventory"))
        self.assertTrue(ada.command(token, "fly to mars").startswith("You fly to Mars."))


if __name__ == "__main__":
    unittest.main()