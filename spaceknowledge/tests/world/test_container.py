"""Unit tests for world/container.py."""

import unittest

from spaceknowledge.world.container import Container
from spaceknowledge.world.item import PlainItem


class TestContainer(unittest.TestCase):

    def setUp(self):
        # A chest holding a box holding a key.
        self.key = PlainItem("key-1", "key", "a brass key")
        self.box = Container("box-1", "box", "a small box")
        self.chest = Container("chest-1", "chest", "an old chest")
        self.box.add(self.key)
        self.chest.add(self.box)

    def test_count_is_direct_contents_but_total_is_every_depth(self):
        self.assertEqual(1, self.chest.count())          # only the box
        self.assertEqual(2, self.chest.total_inside())   # the box and the key

    def test_find_looks_one_level_but_find_deep_looks_everywhere(self):
        self.assertIsNone(self.chest.find("key-1"))
        self.assertIs(self.key, self.chest.find_deep("key-1"))

    def test_a_container_cannot_contain_itself(self):
        with self.assertRaises(ValueError):
            self.chest.add(self.chest)

    def test_describe_goes_all_the_way_down(self):
        self.assertEqual("an old chest, holding a small box, holding a brass key",
                         self.chest.describe())
        self.assertEqual("a small box, empty",
                         Container("box-2", "box", "a small box").describe())


if __name__ == "__main__":
    unittest.main()