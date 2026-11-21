"""Unit tests for world/item.py."""

import unittest

from spaceknowledge.world.item import Item, PlainItem


class TestItem(unittest.TestCase):

    def test_a_bare_item_cannot_be_made(self):
        with self.assertRaises(TypeError):     # Item is abstract
            Item("torch-1", "torch")

    def test_a_plain_item_describes_itself_and_holds_nothing(self):
        torch = PlainItem("torch-1", "torch", "a battered torch")
        self.assertEqual("torch-1", torch.item_id)
        self.assertEqual("torch", torch.name)
        self.assertEqual("a battered torch", torch.describe())
        self.assertEqual(0, torch.total_inside())

    def test_an_item_needs_an_id(self):
        with self.assertRaises(ValueError):
            PlainItem("", "torch", "a torch")


if __name__ == "__main__":
    unittest.main()