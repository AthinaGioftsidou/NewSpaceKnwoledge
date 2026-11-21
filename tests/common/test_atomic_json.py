"""Unit tests for common/atomic_json.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from spaceknowledge.common.atomic_json import write_json_atomically


class TestAtomicJson(unittest.TestCase):

    def setUp(self):
        # Runs before EVERY test: a fresh empty folder, deleted afterwards.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "state" / "players.json"

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_writes_the_file_and_creates_the_folder(self):
        write_json_atomically(self.path, {"ada": ["torch"]})
        self.assertEqual({"ada": ["torch"]}, self.read())

    def test_new_save_replaces_old_save(self):
        write_json_atomically(self.path, {"version": 1})
        write_json_atomically(self.path, {"version": 2})
        self.assertEqual({"version": 2}, self.read())

    def test_failed_save_keeps_old_file_and_leaves_no_temp_file(self):
        write_json_atomically(self.path, {"version": 1})
        # Pretend the disk fails at the very last step.
        with mock.patch("spaceknowledge.common.atomic_json.os.replace",
                        side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                write_json_atomically(self.path, {"version": 2})
        self.assertEqual({"version": 1}, self.read())
        self.assertEqual([], list(self.path.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()