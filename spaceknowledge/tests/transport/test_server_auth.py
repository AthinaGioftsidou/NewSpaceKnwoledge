"""Unit tests for transport/server_auth.py."""

import tempfile
import unittest
from pathlib import Path

from spaceknowledge.common.messages import Request
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.channel import InMemoryChannel
from spaceknowledge.transport.server_auth import (
    AuthenticatedChannel, CorruptKeyError, ServerAuthError, ServerIdentity, handshake,
    load_or_create_key,
)

KEY = bytes(range(32))           # a fixed 32-byte key, so tests are repeatable
OTHER_KEY = bytes(range(1, 33))


class TestKeyFile(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "state" / "server.key"

    def test_the_key_is_created_once_then_read_back(self):
        created = load_or_create_key(self.path)
        self.assertEqual(32, len(created))
        self.assertEqual(64, len(self.path.read_text(encoding="ascii")))   # stored as hex
        self.assertEqual(created, load_or_create_key(self.path))           # same key next time

    def test_a_damaged_key_file_is_refused(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("not a key", encoding="ascii")
        with self.assertRaises(CorruptKeyError):
            load_or_create_key(self.path)


class TestHandshake(unittest.TestCase):

    def test_two_servers_with_the_same_key_trust_each_other(self):
        self.assertIsNone(handshake(ServerIdentity("broker", KEY), ServerIdentity("universe", KEY)))

    def test_different_keys_are_refused(self):
        refusal = handshake(ServerIdentity("broker", KEY), ServerIdentity("universe", OTHER_KEY))
        self.assertIn("do not share the same server key", refusal.why)

    def test_two_servers_with_one_name_are_refused(self):
        self.assertIsNotNone(handshake(ServerIdentity("broker", KEY), ServerIdentity("broker", KEY)))

    def test_a_proof_is_tied_to_the_challenge_and_to_the_signer(self):
        universe, broker = ServerIdentity("universe", KEY), ServerIdentity("broker", KEY)
        challenge, answer_nonce = universe.new_nonce(), broker.new_nonce()
        proof = broker.prove(answer_nonce, challenge)
        self.assertTrue(universe.verify("broker", challenge, answer_nonce, proof))
        # Replayed against a NEW challenge: useless.
        self.assertFalse(universe.verify("broker", universe.new_nonce(), answer_nonce, proof))
        # Claimed to be from someone else: useless.
        self.assertFalse(universe.verify("broker-2", challenge, answer_nonce, proof))

    def test_a_key_that_is_too_short_is_refused(self):
        with self.assertRaises(ValueError):
            ServerIdentity("broker", b"short")


class TestAuthenticatedChannel(unittest.TestCase):

    def test_a_trusted_channel_passes_requests_through(self):
        channel = AuthenticatedChannel(InMemoryChannel(a_universe()),
                                       ServerIdentity("broker", KEY), ServerIdentity("universe", KEY))
        self.assertTrue(channel.send(Request("op1", "join", "ada", "earth")).ok)

    def test_an_untrusted_channel_is_never_made(self):
        with self.assertRaises(ServerAuthError) as caught:
            AuthenticatedChannel(InMemoryChannel(a_universe()),
                                 ServerIdentity("broker", KEY), ServerIdentity("universe", OTHER_KEY))
        self.assertIsInstance(caught.exception, ConnectionError)


if __name__ == "__main__":
    unittest.main()