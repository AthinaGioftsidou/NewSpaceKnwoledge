"""Unit tests for transport/socket_channel.py and universe_listener.py,
over real connections on this computer (127.0.0.1)."""

import unittest

from spaceknowledge.common.messages import Request
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.server_auth import ServerAuthError, ServerIdentity
from spaceknowledge.transport.socket_channel import SocketChannel
from spaceknowledge.transport.universe_listener import UniverseListener

KEY = bytes(range(32))
OTHER_KEY = bytes(range(1, 33))


class TestSocketConnection(unittest.TestCase):

    def start_listener(self, name="universe", key=KEY):
        """A Universe listening on a free port (port 0: the system picks one)."""
        listener = UniverseListener(a_universe(), ServerIdentity(name, key),
                                    peers=("broker-1", "broker-2"))
        listener.start()
        self.addCleanup(listener.stop)
        return listener

    def connect(self, listener, name="broker-1", key=KEY):
        host, port = listener.address
        channel = SocketChannel(host, port, ServerIdentity(name, key), timeout=2)
        self.addCleanup(channel.close)
        return channel

    def test_a_request_crosses_the_network_and_comes_back(self):
        channel = self.connect(self.start_listener())
        self.assertTrue(channel.send(Request("op1", "join", "ada", "earth")).ok)
        self.assertEqual("Earth", channel.send(Request("op2", "where", "ada", "here")).items[0].name)

    def test_two_brokers_share_one_universe(self):
        listener = self.start_listener()
        one, two = self.connect(listener, "broker-1"), self.connect(listener, "broker-2")
        one.send(Request("a1", "join", "ada", "earth"))
        two.send(Request("b1", "join", "bob", "earth"))
        one.send(Request("a2", "add_item", "ada", "torch-1", name="torch"))
        seen_by_bob = two.send(Request("b2", "look", "bob", "here"))
        self.assertEqual(["torch"], [item.name for item in seen_by_bob.items])

    def test_a_broker_with_the_wrong_key_is_turned_away(self):
        channel = self.connect(self.start_listener(), key=OTHER_KEY)
        with self.assertRaises(ServerAuthError):
            channel.send(Request("op1", "join", "ada", "earth"))

    def test_a_broker_that_is_not_on_the_list_is_turned_away(self):
        channel = self.connect(self.start_listener(), name="stranger")
        with self.assertRaises(ServerAuthError):
            channel.send(Request("op1", "join", "ada", "earth"))

    def test_a_fake_universe_is_not_trusted_by_the_broker(self):
        channel = self.connect(self.start_listener(name="impostor"))
        with self.assertRaises(ServerAuthError):
            channel.send(Request("op1", "join", "ada", "earth"))

    def test_a_dropped_connection_is_reopened_once(self):
        listener = self.start_listener()
        channel = self.connect(listener)
        channel.send(Request("op1", "join", "ada", "earth"))
        listener.disconnect_all()                   # the line goes dead
        self.assertTrue(channel.send(Request("op2", "where", "ada", "here")).ok)

    def test_nobody_listening_is_a_connection_error(self):
        listener = self.start_listener()
        channel = self.connect(listener)
        listener.stop()
        with self.assertRaises(ConnectionError):
            channel.send(Request("op1", "join", "ada", "earth"))

    def test_a_listener_needs_sensible_peers(self):
        for peers in ((), ("universe",)):          # nobody, or itself
            with self.subTest(peers=peers):
                with self.assertRaises(ValueError):
                    UniverseListener(a_universe(), ServerIdentity("universe", KEY), peers=peers)


if __name__ == "__main__":
    unittest.main()