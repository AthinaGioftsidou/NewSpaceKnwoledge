"""Unit tests for world/world.py."""

import unittest

from spaceknowledge.world.destination import Destination
from spaceknowledge.world.world import World


class TestWorld(unittest.TestCase):

    def setUp(self):
        self.places = {"earth": Destination("earth", "Earth", "Home."),
                       "moon": Destination("moon", "The Moon", "Grey.")}

    def test_the_start_must_be_in_the_world(self):
        with self.assertRaises(ValueError):
            World(self.places, "mars")

    def test_a_world_cannot_be_empty(self):
        with self.assertRaises(ValueError):
            World({}, "earth")

    def test_destinations_are_found_by_name(self):
        world = World(self.places, "earth")
        self.assertEqual("Earth", world.start_destination.name)
        self.assertEqual("The Moon", world.destination("moon").name)
        with self.assertRaises(KeyError):
            world.destination("pluto")

    def test_the_world_keeps_its_own_copy(self):
        world = World(self.places, "earth")
        self.places.clear()                        # the caller changes ITS dict...
        self.assertEqual(2, world.destination_count())   # ...the world is not affected
        self.assertEqual(["earth", "moon"], world.destination_ids())


if __name__ == "__main__":
    unittest.main()