"""Unit tests for app/paths.py, app/layout.py and app/keys.py."""

import tempfile
import unittest
from pathlib import Path

from spaceknowledge.app.keys import MissingKeyError, read_existing_key
from spaceknowledge.app.layout import PROJECT, STATE_ROOT, WORLD_FILE, broker_state_dir
from spaceknowledge.app.paths import MAILBOX_FILE
from spaceknowledge.transport.server_auth import load_or_create_key


class TestLayout(unittest.TestCase):

    def test_the_world_file_is_found_from_the_project_folder(self):
        self.assertEqual(PROJECT / "data" / "space.json", WORLD_FILE)
        self.assertTrue(WORLD_FILE.exists())

    def test_each_broker_has_its_own_folder(self):
        self.assertEqual(STATE_ROOT / "broker-1", broker_state_dir("broker-1"))
        self.assertEqual(Path("mailbox") / "admin_mailbox.txt", MAILBOX_FILE)

    def test_a_name_can_never_escape_the_state_folder(self):
        for name in ("../../windows", "universe", "a/b"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    broker_state_dir(name)


class TestKeys(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "universe" / "server.key"

    def test_a_broker_never_creates_the_key(self):
        with self.assertRaisesRegex(MissingKeyError, "start the Universe first"):
            read_existing_key(self.path)
        self.assertFalse(self.path.exists())             # still not there

    def test_a_broker_reads_the_key_the_universe_made(self):
        made = load_or_create_key(self.path)             # what the Universe does
        self.assertEqual(made, read_existing_key(self.path))


if __name__ == "__main__":
    unittest.main()