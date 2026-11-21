"""Unit tests for world/destination.py."""

import unittest

from spaceknowledge.world.container import Container
from spaceknowledge.world.destination import Destination
from spaceknowledge.world.door import Door
from spaceknowledge.world.holder import AmbiguousName
from spaceknowledge.world.item import PlainItem


class TestDestination(unittest.TestCase):

    def setUp(self):
        self.earth = Destination("earth", "Earth", "Our home planet.")
        self.moon = Destination("moon", "The Moon", "Grey and airless.")
        self.mars = Destination("mars", "Mars", "The red planet.")
        self.gate = Door("mars_gate", "launch gate", "mission:ship_upgrade")

    def test_an_exit_goes_one_way_only(self):
        self.earth.add_exit("moon", self.moon)
        self.assertIs(self.moon, self.earth.exit_to("moon"))
        self.assertIsNone(self.moon.exit_to("earth"))     # the way back is a second call

    def test_directions_ignore_case(self):
        self.earth.add_exit("Moon", self.moon)
        self.assertIs(self.moon, self.earth.exit_to("MOON"))
        self.assertEqual(["moon"], self.earth.exits())

    def test_a_locked_route_still_exists(self):
        self.earth.add_exit("mars", self.mars, self.gate)
        self.assertIs(self.mars, self.earth.exit_to("mars"))        # the map: yes, a route
        self.assertFalse(self.earth.door_to("mars").is_passable())  # the rule: not now
        self.assertIsNone(self.earth.door_to("moon"))               # no door at all

    def test_one_door_shared_by_two_sides(self):
        self.earth.add_exit("mars", self.mars, self.gate)
        self.mars.add_exit("earth", self.earth, self.gate)
        self.earth.door_to("mars").unlock("mission:ship_upgrade")
        self.assertTrue(self.mars.door_to("earth").is_passable())

    def test_describe_shows_items_exits_and_closed_doors(self):
        self.earth.add_item(PlainItem("torch-1", "torch", "a battered torch"))
        self.earth.add_exit("moon", self.moon)
        self.earth.add_exit("mars", self.mars, self.gate)
        self.assertEqual(
            "Earth\nOur home planet.\n"
            "There is a battered torch here.\n"
            "Exits: mars, moon\n"
            "The launch gate mars is locked.",
            self.earth.describe(),
        )
        self.gate.unlock("mission:ship_upgrade")
        self.assertNotIn("launch gate", self.earth.describe())   # an open door is not mentioned

    def test_open_container_holding_refuses_an_ambiguous_name(self):
        for number in (1, 2):
            chest = Container(f"chest-{number}", "chest", "an old chest")
            chest.add(PlainItem(f"key-{number}", "key", "a brass key"))
            self.mars.add_item(chest)
        with self.assertRaises(AmbiguousName):
            self.mars.open_container_holding("key")              # which chest's key?
        self.assertEqual("chest-2", self.mars.open_container_holding("key-2").item_id)  # an id is exact


if __name__ == "__main__":
    unittest.main()