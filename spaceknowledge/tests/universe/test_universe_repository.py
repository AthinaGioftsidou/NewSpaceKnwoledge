"""Unit tests for universe/universe_repository.py."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.common.messages import ItemInfo, Response
from spaceknowledge.common.refusal import Refusal
from spaceknowledge.universe.universe_repository import (
    CorruptStateError, InMemoryUniverseRepository, JsonUniverseRepository, UniverseState,
)


def a_state():
    """A small state with one of everything, including both kinds of answer."""
    return UniverseState(
        locations={"ada": "earth"},
        stock={"earth": {"iron": 480}},
        dropped={"earth": ["torch-1"]},
        answers={
            "op1": Response("op1", items=(ItemInfo("torch-1", "torch", "a torch"),)),
            "op2": Response("op2", Refusal("mine gold", "there is no gold", "mine iron")),
        },
        names={"torch-1": "torch"},
        missions={"ship_upgrade": {"collected": 20, "complete": False}},
    )


class TestUniverseRepository(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "universe.json"

    def write(self, document):
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_nothing_saved_yet_is_none(self):
        self.assertIsNone(InMemoryUniverseRepository().load())
        self.assertIsNone(JsonUniverseRepository(self.path).load())

    def test_both_repositories_give_back_what_was_saved(self):
        # The same contract, two storages: this is the point of the pattern.
        for repository in (InMemoryUniverseRepository(), JsonUniverseRepository(self.path)):
            with self.subTest(repository=type(repository).__name__):
                repository.save(a_state())
                loaded = repository.load()
                self.assertEqual({"ada": "earth"}, loaded.locations)
                self.assertEqual({"earth": {"iron": 480}}, loaded.stock)
                self.assertEqual("torch", loaded.answers["op1"].items[0].name)
                self.assertEqual("there is no gold", loaded.answers["op2"].refusal.why)
                self.assertEqual(20, loaded.missions["ship_upgrade"]["collected"])

    def test_the_in_memory_store_hands_out_copies(self):
        repository = InMemoryUniverseRepository()
        repository.save(a_state())
        repository.load().stock["earth"]["iron"] = 0       # change what was loaded...
        self.assertEqual(480, repository.load().stock["earth"]["iron"])   # ...store unchanged

    def test_an_older_file_without_names_or_missions_still_loads(self):
        self.write({"version": 1, "locations": {}, "stock": {}, "dropped": {}, "answers": {}})
        loaded = JsonUniverseRepository(self.path).load()
        self.assertEqual({}, loaded.names)
        self.assertEqual({}, loaded.missions)

    def test_a_file_that_cannot_be_trusted_is_refused(self):
        good = {"version": 1, "locations": {}, "stock": {}, "dropped": {}, "answers": {}}
        bad_files = {
            "wrong version":      {**good, "version": 2},
            "negative stock":     {**good, "stock": {"earth": {"iron": -1}}},
            "dropped twice":      {**good, "dropped": {"earth": ["t1", "t1"]}},
            "refusal no details": {**good, "answers": {"op1": {"ok": False}}},
        }
        for reason, document in bad_files.items():
            with self.subTest(reason=reason):
                self.write(document)
                with self.assertRaises(CorruptStateError):
                    JsonUniverseRepository(self.path).load()

    def test_a_file_that_is_not_json_is_refused(self):
        self.path.write_text("{ this is not json", encoding="utf-8")
        with self.assertRaises(CorruptStateError):
            JsonUniverseRepository(self.path).load()


if __name__ == "__main__":
    unittest.main()