"""Unit tests for world/builder.py."""

import unittest

from spaceknowledge.world.builder import DestinationBuilder
from spaceknowledge.world.item import PlainItem


class TestDestinationBuilder(unittest.TestCase):

    def test_builds_a_destination_from_its_parts(self):
        mars = (DestinationBuilder("mars")
                .named("Mars")
                .described("The red planet.")
                .holding(PlainItem("rock-1", "rock", "a red rock"))
                .build())
        self.assertEqual("Mars", mars.name)
        self.assertEqual("The red planet.", mars.description)
        self.assertEqual(1, mars.item_count())

    def test_a_destination_must_be_named(self):
        with self.assertRaises(ValueError):
            DestinationBuilder("mars").described("The red planet.").build()

    def test_a_builder_can_be_used_only_once(self):
        builder = DestinationBuilder("mars").named("Mars")
        builder.build()
        with self.assertRaises(ValueError):
            builder.build()

    def test_only_items_can_be_held(self):
        with self.assertRaises(TypeError):
            DestinationBuilder("mars").holding("a rock")


if __name__ == "__main__":
    unittest.main()