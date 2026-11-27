"""Unit tests for broker/pending_repository.py: the notebook of operations in flight."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.broker.pending_repository import (
    CorruptPendingError, InMemoryPendingRepository, JsonPendingRepository,
)
from spaceknowledge.common.messages import Request

PENDING = [Request("run1-op7", "add_item", "ada", "torch-1", name="torch"),
           Request("run1-op8", "mine", "ada", "iron", 5)]


class TestPendingRepository(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "pending.json"

    def write(self, document):
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_nothing_saved_yet_is_empty(self):
        self.assertEqual([], JsonPendingRepository(self.path).load())

    def test_both_repositories_give_the_operations_back_in_order(self):
        for notebook in (InMemoryPendingRepository(), JsonPendingRepository(self.path)):
            with self.subTest(notebook=type(notebook).__name__):
                notebook.save(PENDING)
                back = notebook.load()
                self.assertEqual(["run1-op7", "run1-op8"], [r.op_id for r in back])
                self.assertEqual(("add_item", "torch-1", "torch"),
                                 (back[0].action, back[0].item_id, back[0].name))
                self.assertEqual(5, back[1].amount)

    def test_the_file_is_plain_readable_json(self):
        JsonPendingRepository(self.path).save(PENDING[:1])
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual({"version": 1, "pending": [{
            "op_id": "run1-op7", "action": "add_item", "player_id": "ada",
            "item_id": "torch-1", "amount": 1, "name": "torch"}]}, saved)

    def test_a_refused_save_keeps_the_old_list(self):
        for notebook in (InMemoryPendingRepository(), JsonPendingRepository(self.path)):
            with self.subTest(notebook=type(notebook).__name__):
                notebook.save(PENDING)
                with self.assertRaises(ValueError):
                    notebook.save(PENDING + PENDING)                  # an op_id twice
                self.assertEqual(2, len(notebook.load()))

    def test_a_file_that_cannot_be_trusted_is_refused(self):
        good = {"op_id": "o1", "action": "mine", "player_id": "ada", "item_id": "iron",
                "amount": 1, "name": None}
        bad_files = {
            "not json":       None,
            "wrong version":  {"version": 2, "pending": []},
            "no list":        {"version": 1},
            "zero amount":    {"version": 1, "pending": [{**good, "amount": 0}]},
            "extra field":    {"version": 1, "pending": [{**good, "admin": True}]},
            "missing field":  {"version": 1, "pending": [{k: v for k, v in good.items()
                                                         if k != "player_id"}]},
            "op_id twice":    {"version": 1, "pending": [good, good]},
        }
        for reason, document in bad_files.items():
            with self.subTest(reason=reason):
                if document is None:
                    self.path.write_text("{ broken", encoding="utf-8")
                else:
                    self.write(document)
                with self.assertRaises(CorruptPendingError):
                    JsonPendingRepository(self.path).load()


if __name__ == "__main__":
    unittest.main()