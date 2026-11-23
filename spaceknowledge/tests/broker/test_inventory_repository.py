"""Unit tests for broker/inventory_repository.py."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.broker.inventory_repository import (
    CorruptStoreError, InMemoryInventoryRepository, JsonInventoryRepository,
)
from spaceknowledge.common.messages import Request

RECORDS = {"ada": [("torch-1", "torch")], "bob": []}
RESOURCES = {"ada": {"iron": 20}}
PENDING = [Request("run1-op7", "add_item", "ada", "torch-1", name="torch")]


class TestInventoryRepository(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "players.json"

    def write(self, document):
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_nothing_saved_yet_is_empty(self):
        repository = JsonInventoryRepository(self.path)
        self.assertEqual(({}, {}, []), (repository.load(), repository.load_resources(),
                                        repository.load_pending()))

    def test_both_repositories_give_back_items_resources_and_pending(self):
        for repository in (InMemoryInventoryRepository(), JsonInventoryRepository(self.path)):
            with self.subTest(repository=type(repository).__name__):
                repository.save(RECORDS, RESOURCES, PENDING)
                self.assertEqual(RECORDS, repository.load())
                self.assertEqual({"ada": {"iron": 20}, "bob": {}}, repository.load_resources())
                pending = repository.load_pending()
                self.assertEqual(("run1-op7", "add_item", "torch"),
                                 (pending[0].op_id, pending[0].action, pending[0].name))

    def test_a_refused_save_keeps_the_old_data(self):
        for repository in (InMemoryInventoryRepository(), JsonInventoryRepository(self.path)):
            with self.subTest(repository=type(repository).__name__):
                repository.save(RECORDS, RESOURCES, PENDING)
                with self.assertRaises(ValueError):                  # a stranger's bag
                    repository.save(RECORDS, {"eve": {"iron": 1}})
                with self.assertRaises(ValueError):                  # one op twice
                    repository.save(RECORDS, RESOURCES, PENDING + PENDING)
                self.assertEqual(RESOURCES["ada"], repository.load_resources()["ada"])
                self.assertEqual(1, len(repository.load_pending()))

    def test_older_files_still_load(self):
        self.write({"version": 1, "players": {"ada": [{"id": "torch-1", "name": "torch"}]}})
        repository = JsonInventoryRepository(self.path)
        self.assertEqual({"ada": [("torch-1", "torch")]}, repository.load())
        self.assertEqual({"ada": {}}, repository.load_resources())
        self.assertEqual([], repository.load_pending())

    def test_a_file_that_cannot_be_trusted_is_refused(self):
        ada = {"items": [{"id": "t1", "name": "torch"}], "resources": {}}
        bad_files = {
            "wrong version":    {"version": 9, "players": {}},
            "item twice":       {"version": 2, "players": {"ada": {
                                 "items": [{"id": "t1", "name": "torch"}] * 2, "resources": {}}}},
            "zero iron":        {"version": 2, "players": {"ada": {**ada, "resources": {"iron": 0}}}},
            "pending stranger": {"version": 3, "players": {"ada": ada}, "pending": [
                                 {"op_id": "o1", "action": "mine", "player_id": "eve",
                                  "item_id": "iron", "amount": 1, "name": None}]},
        }
        for reason, document in bad_files.items():
            with self.subTest(reason=reason):
                self.write(document)
                with self.assertRaises(CorruptStoreError):
                    JsonInventoryRepository(self.path).load()


if __name__ == "__main__":
    unittest.main()