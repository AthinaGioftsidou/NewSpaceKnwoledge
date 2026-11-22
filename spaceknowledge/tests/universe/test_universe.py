"""Unit tests for universe/universe.py, played on the real data/space.json."""

import json
import unittest
from itertools import count
from pathlib import Path

from spaceknowledge.common.messages import Request
from spaceknowledge.universe.deposits import Deposits
from spaceknowledge.universe.missions import MissionBook
from spaceknowledge.universe.universe import Universe
from spaceknowledge.universe.universe_repository import (
    CorruptStateError, InMemoryUniverseRepository, UniverseState,
)
from spaceknowledge.world.loader import StandardWorldLoader

SPACE_FILE = Path(__file__).resolve().parents[3] / "data" / "space.json"


def a_universe(repository=None, raw=None):
    """A fresh Universe built from space.json, the same way the real game builds it."""
    raw = raw or json.loads(SPACE_FILE.read_text(encoding="utf-8"))
    return Universe(
        StandardWorldLoader().build(raw),
        Deposits.from_raw(raw),
        repository or InMemoryUniverseRepository(),
        missions=MissionBook.from_raw(raw),
    )


class TestUniverse(unittest.TestCase):

    def setUp(self):
        self.repository = InMemoryUniverseRepository()
        self.universe = a_universe(self.repository)
        self.numbers = count(1)
        self.ask("join", "earth")                       # ada starts on Earth

    def ask(self, action, target, amount=1, name=None, op_id=None):
        """Send one request as ada. Each gets a new op_id unless one is given."""
        op_id = op_id or f"op{next(self.numbers)}"
        return self.universe.handle(Request(op_id, action, "ada", target, amount, name))

    def test_join_places_a_player_once(self):
        self.assertEqual("earth", self.universe.location_of("ada"))
        self.ask("fly", "moon")
        self.ask("join", "earth")                       # joining again changes nothing
        self.assertEqual("moon", self.universe.location_of("ada"))
        self.assertFalse(self.ask("join", "pluto").ok)

    def test_a_player_the_universe_does_not_know_is_refused(self):
        response = self.universe.handle(Request("x1", "look", "bob", "here"))
        self.assertIn("does not know where bob is", response.refusal.why)

    def test_mining_takes_from_the_planet_and_has_limits(self):
        self.assertTrue(self.ask("mine", "iron", 5).ok)
        self.assertIn("only 495 iron left", self.ask("mine", "iron", 1000).refusal.why)
        self.assertIn("no gold to mine", self.ask("mine", "gold").refusal.why)

    def test_the_same_op_id_twice_is_done_once(self):
        first = self.ask("mine", "iron", 5, op_id="same")
        again = self.ask("mine", "iron", 5, op_id="same")      # e.g. resent after a crash
        self.assertIs(first, again)                            # the remembered answer
        self.assertIn("only 495 iron left", self.ask("mine", "iron", 1000).refusal.why)

    def test_questions_that_change_nothing_are_not_remembered(self):
        before = self.universe.answer_count()
        self.ask("look", "here")
        self.ask("where", "here")
        self.ask("mission", "here")
        self.assertEqual(before, self.universe.answer_count())

    def test_flying_needs_a_route_and_an_open_way(self):
        self.assertIn("no route to pluto", self.ask("fly", "pluto").refusal.why)
        self.assertIn("The launch gate is locked", self.ask("fly", "mars").refusal.why)
        arrived = self.ask("fly", "moon")
        self.assertEqual("The Moon", arrived.items[0].name)

    def test_the_mission_opens_the_way_to_mars(self):
        self.ask("mine", "iron", 20)
        self.assertEqual("question", self.ask("mission", "here").items[0].item_id)
        wrong = self.ask("answer", "copper")
        self.assertIn("rust is what happens", wrong.refusal.next_step)   # the hint
        self.assertTrue(self.ask("answer", "iron").ok)
        self.assertEqual("Mars", self.ask("fly", "mars").items[0].name)

    def test_a_dropped_item_can_be_picked_up_once(self):
        self.ask("add_item", "torch-1", name="torch")
        self.assertEqual(["torch"], [i.name for i in self.ask("look", "here").items])
        picked = self.ask("pick", "torch-1")
        self.assertEqual("torch", picked.items[0].name)
        self.assertIn("may already have been picked up", self.ask("pick", "torch-1").refusal.why)

    def test_a_restart_carries_on_where_it_stopped(self):
        self.ask("mine", "iron", 20)
        self.ask("answer", "iron")
        self.ask("add_item", "torch-1", name="torch")
        restarted = a_universe(self.repository)                # same storage, fresh objects
        self.assertEqual("earth", restarted.location_of("ada"))
        self.assertEqual(["torch"], [i.name for i in
                         restarted.handle(Request("r1", "look", "ada", "here")).items])
        self.assertTrue(restarted.handle(Request("r2", "fly", "ada", "mars")).ok)  # gate re-opened

    def test_an_unknown_action_is_refused(self):
        self.assertIn("send one of:", self.ask("dance", "here").refusal.next_step)

    def test_saved_state_that_does_not_fit_the_world_is_refused(self):
        repository = InMemoryUniverseRepository()
        repository.save(UniverseState({"ada": "pluto"}, {}, {}, {}))
        with self.assertRaises(CorruptStateError):
            a_universe(repository)

    def test_a_mission_must_open_a_real_mission_door(self):
        raw = json.loads(SPACE_FILE.read_text(encoding="utf-8"))
        raw["missions"][0]["opens"]["direction"] = "moon"      # there is no gate on that route
        with self.assertRaises(ValueError):
            a_universe(raw=raw)


if __name__ == "__main__":
    unittest.main()