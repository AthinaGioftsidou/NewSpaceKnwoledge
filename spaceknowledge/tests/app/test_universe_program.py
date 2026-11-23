"""Unit tests for app/universe_program.py: the Universe as its own program."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.app.layout import WORLD_FILE
from spaceknowledge.app.universe_program import start_universe
from spaceknowledge.common.messages import Request
from spaceknowledge.transport.server_auth import ServerIdentity, load_or_create_key
from spaceknowledge.transport.socket_channel import SocketChannel
from spaceknowledge.universe.universe_repository import CorruptStateError


class TestUniverseProgram(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.state = Path(folder.name)

    def test_a_broker_can_connect_with_the_key_it_created(self):
        process = start_universe(WORLD_FILE, self.state, port=0, peers=("broker-1",))
        self.addCleanup(process.close)
        key = load_or_create_key(self.state / "server.key")      # made by start_universe
        host, port = process.address
        channel = SocketChannel(host, port, ServerIdentity("broker-1", key), timeout=2)
        self.addCleanup(channel.close)
        self.assertTrue(channel.send(Request("op1", "join", "ada", "earth")).ok)
        self.assertEqual("earth", process.universe.location_of("ada"))

    def test_a_damaged_save_stops_the_start(self):
        (self.state / "universe.json").write_text(json.dumps({"version": 99}), encoding="utf-8")
        with self.assertRaises(CorruptStateError):
            start_universe(WORLD_FILE, self.state, port=0)


if __name__ == "__main__":
    unittest.main()