"""Unit tests for world/holder.py."""

import unittest

from spaceknowledge.world.holder import AmbiguousName, ItemHolder
from spaceknowledge.world.item import PlainItem


class TestItemHolder(unittest.TestCase):

    def setUp(self):
        self.holder = ItemHolder()
        self.torch = PlainItem("torch-1", "Torch", "a torch")
        self.holder.add(self.torch)

    def test_two_items_with_one_id_are_refused(self):
        with self.assertRaises(ValueError):
            self.holder.add(PlainItem("torch-1", "lamp", "a lamp"))

    def test_find_says_none_but_remove_raises(self):
        self.assertIsNone(self.holder.find("nothing"))   # asking is a fair question
        with self.assertRaises(KeyError):                # removing what is not here is a mistake
            self.holder.remove("nothing")

    def test_match_finds_by_id_or_by_name_in_any_case(self):
        self.assertIs(self.torch, self.holder.match("torch-1"))
        self.assertIs(self.torch, self.holder.match("  TORCH "))
        self.assertIsNone(self.holder.match("lamp"))

    def test_two_items_with_the_same_name_are_ambiguous(self):
        self.holder.add(PlainItem("torch-2", "torch", "another torch"))
        with self.assertRaises(AmbiguousName) as caught:
            self.holder.match("torch")
        self.assertEqual("Which Torch? torch-1, torch-2", str(caught.exception))

    def test_contents_is_a_copy(self):
        self.holder.contents().clear()
        self.assertEqual(1, self.holder.count())


if __name__ == "__main__":
    unittest.main()