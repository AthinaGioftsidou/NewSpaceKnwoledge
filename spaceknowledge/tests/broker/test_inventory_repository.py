"""Unit tests for broker/inventory_repository.py."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.broker.inventory_repository import (
    CorruptStoreError, InMemoryInventoryRepository, JsonInventoryRepository,
)

RECORDS = {"ada": [("torch-1", "torch")], "bob": []}
RESOURCES = {"ada": {"iron": 20}}
SETTLED = {"run1-op7"}


class TestInventoryRepository(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "players.json"

    def write(self, document):
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_nothing_saved_yet_is_empty(self):
        repository = JsonInventoryRepository(self.path)
        self.assertEqual(({}, {}, set()), (repository.load(), repository.load_resources(),
                                           repository.load_settled()))

    def test_both_repositories_give_back_items_resources_and_settled(self):
        for repository in (InMemoryInventoryRepository(), JsonInventoryRepository(self.path)):
            with self.subTest(repository=type(repository).__name__):
                repository.save(RECORDS, RESOURCES, SETTLED)
                self.assertEqual(RECORDS, repository.load())
                self.assertEqual({"ada": {"iron": 20}, "bob": {}}, repository.load_resources())
                self.assertEqual(SETTLED, repository.load_settled())

    def test_the_file_holds_no_pending_operations(self):
        JsonInventoryRepository(self.path).save(RECORDS, RESOURCES, SETTLED)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual({"version", "players", "settled"}, set(saved))   # pending.json has them

    def test_a_refused_save_keeps_the_old_data(self):
        for repository in (InMemoryInventoryRepository(), JsonInventoryRepository(self.path)):
            with self.subTest(repository=type(repository).__name__):
                repository.save(RECORDS, RESOURCES, SETTLED)
                with self.assertRaises(ValueError):                  # a stranger's bag
                    repository.save(RECORDS, {"eve": {"iron": 1}})
                with self.assertRaises(ValueError):                  # an empty op_id
                    repository.save(RECORDS, RESOURCES, {""})
                self.assertEqual(RESOURCES["ada"], repository.load_resources()["ada"])
                self.assertEqual(SETTLED, repository.load_settled())

    def test_older_files_still_load(self):
        self.write({"version": 1, "players": {"ada": [{"id": "torch-1", "name": "torch"}]}})
        repository = JsonInventoryRepository(self.path)
        self.assertEqual({"ada": [("torch-1", "torch")]}, repository.load())
        self.assertEqual({"ada": {}}, repository.load_resources())
        self.assertEqual(set(), repository.load_settled())
        ada = {"items": [], "resources": {}}
        self.write({"version": 3, "players": {"ada": ada}, "pending": []})   # nothing in flight
        self.assertEqual({"ada": []}, JsonInventoryRepository(self.path).load())

    def test_a_file_that_cannot_be_trusted_is_refused(self):
        ada = {"items": [{"id": "t1", "name": "torch"}], "resources": {}}
        bad_files = {
            "wrong version":    {"version": 9, "players": {}},
            "item twice":       {"version": 2, "players": {"ada": {
                                 "items": [{"id": "t1", "name": "torch"}] * 2, "resources": {}}}},
            "zero iron":        {"version": 2, "players": {"ada": {**ada, "resources": {"iron": 0}}}},
            "old and in flight": {"version": 3, "players": {"ada": ada}, "pending": [
                                 {"op_id": "o1", "action": "mine", "player_id": "ada",
                                  "item_id": "iron", "amount": 1, "name": None}]},
            "settled twice":    {"version": 4, "players": {"ada": ada}, "settled": ["o1", "o1"]},
            "settled not text": {"version": 4, "players": {"ada": ada}, "settled": [7]},
        }
        for reason, document in bad_files.items():
            with self.subTest(reason=reason):
                self.write(document)
                with self.assertRaises(CorruptStoreError):
                    JsonInventoryRepository(self.path).load()


if __name__ == "__main__":
    unittest.main()