"""Unit tests for app/broker_program.py: a Broker with its own web door,
talking over the network to a separate Universe."""

import tempfile
import unittest
from pathlib import Path

from spaceknowledge.app.broker_program import start_broker_node
from spaceknowledge.app.keys import MissingKeyError
from spaceknowledge.app.layout import WORLD_FILE
from spaceknowledge.app.universe_program import start_universe
from spaceknowledge.tests.app.helpers import PASSWORD
from spaceknowledge.tests.broker_web.web_helpers import call


class TestBrokerProgram(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.state = Path(folder.name)
        universe = start_universe(WORLD_FILE, self.state / "universe", port=0,
                                  peers=("broker-1", "broker-2"))
        self.addCleanup(universe.close)
        self.universe_address = universe.address

    def a_broker(self, name):
        host, port = self.universe_address
        node = start_broker_node(self.state / name, self.state / "universe" / "server.key",
                                 host, port, "earth", name, web_port=0, iterations=1)
        self.addCleanup(node.close)
        return node

    def play(self, node, player, line):
        call(node, "POST", "/register", {"username": player, "password": PASSWORD})
        token = call(node, "POST", "/login", {"username": player, "password": PASSWORD})[1]["token"]
        return call(node, "POST", "/command", {"line": line}, token=token)[1]["reply"]

    def test_a_player_plays_through_the_broker_over_the_network(self):
        self.assertEqual("You are at Earth.", self.play(self.a_broker("broker-1"), "ada", "where"))

    def test_two_brokers_share_one_galaxy(self):
        one, two = self.a_broker("broker-1"), self.a_broker("broker-2")
        self.assertEqual("You drop the torch.", self.play(one, "ada", "drop torch"))
        seen = self.play(two, "bob", "look")
        self.assertIn("torch", seen)                       # bob, on another Broker, sees it

    def test_a_broker_started_before_the_universe_is_told_why(self):
        with self.assertRaisesRegex(MissingKeyError, "start the Universe first"):
            start_broker_node(self.state / "broker-1", self.state / "nowhere" / "server.key",
                              "127.0.0.1", 7400, "earth", "broker-1", web_port=0)


if __name__ == "__main__":
    unittest.main()