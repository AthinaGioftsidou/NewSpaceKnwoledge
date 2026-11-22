"""Unit tests for world/loader.py, including the real data/space.json."""

import json
import unittest
from pathlib import Path

from spaceknowledge.world.loader import StandardWorldLoader

# tests/world/test_loader.py -> parents[3] is the project folder.
SPACE_FILE = Path(__file__).resolve().parents[3] / "data" / "space.json"


def small_world(**changes):
    """A tiny valid world file as a dict. Pass a key to replace part of it."""
    raw = {
        "start": "earth",
        "destinations": [
            {"id": "earth", "name": "Earth", "description": "Home.", "exits": {"mars": "mars"}},
            {"id": "mars", "name": "Mars", "description": "Red.", "exits": {"earth": "earth"}},
        ],
    }
    raw.update(changes)
    return raw


class TestLoader(unittest.TestCase):

    def setUp(self):
        self.loader = StandardWorldLoader()

    def test_the_real_galaxy_loads(self):
        world = self.loader.load(SPACE_FILE)
        self.assertEqual(["earth", "mars", "moon"], world.destination_ids())
        earth = world.start_destination
        self.assertEqual("earth", earth.destination_id)
        self.assertEqual(["mars", "moon"], earth.exits())
        self.assertFalse(earth.door_to("mars").is_passable())   # locked until the mission
        self.assertIs(earth, world.destination("moon").exit_to("earth"))

    def test_containers_are_built_with_their_contents(self):
        raw = small_world()
        raw["destinations"][1]["items"] = [
            {"kind": "container", "id": "chest-1", "name": "chest", "description": "an old chest",
             "contains": [{"kind": "plain", "id": "key-1", "name": "key", "description": "a brass key"}]},
        ]
        mars = self.loader.build(raw).destination("mars")
        self.assertEqual(1, mars.item_count())    # the chest
        self.assertEqual(2, mars.item_total())    # the chest and the key

    def test_an_item_without_a_known_kind_is_refused(self):
        for item in ({"id": "x", "name": "x", "description": "x"},
                     {"kind": "magic", "id": "x", "name": "x", "description": "x"}):
            with self.subTest(item=item):
                raw = small_world()
                raw["destinations"][0]["items"] = [item]
                with self.assertRaises(ValueError):
                    self.loader.build(raw)

    def test_an_exit_to_an_unknown_destination_is_refused(self):
        raw = small_world()
        raw["destinations"][0]["exits"]["pluto"] = "pluto"
        with self.assertRaises(ValueError):
            self.loader.build(raw)

    def test_a_door_needs_a_key_that_exists_or_a_mission_key(self):
        door = {"id": "gate", "name": "gate", "sides": [{"destination": "earth", "direction": "mars"}]}
        with self.assertRaises(ValueError):                       # no item has this key
            self.loader.build(small_world(doors=[{**door, "key": "lost-key"}]))
        world = self.loader.build(small_world(doors=[{**door, "key": "mission:test"}]))
        self.assertEqual("locked", world.destination("earth").door_to("mars").state_name())

    def test_a_door_must_stand_on_an_exit(self):
        door = {"id": "gate", "name": "gate", "key": "mission:test",
                "sides": [{"destination": "earth", "direction": "moon"}]}   # earth has no moon exit
        with self.assertRaises(ValueError):
            self.loader.build(small_world(doors=[door]))


if __name__ == "__main__":
    unittest.main()