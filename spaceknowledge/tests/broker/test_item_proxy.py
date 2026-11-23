"""Unit tests for broker/item_proxy.py."""

import unittest

from spaceknowledge.broker.item_proxy import ItemProxy
from spaceknowledge.common.messages import ItemInfo
from spaceknowledge.world.item import Item


class TestItemProxy(unittest.TestCase):

    def setUp(self):
        self.calls = []
        picker = lambda proxy, player: self.calls.append((proxy.item_id, player))  # noqa: E731
        self.proxy = ItemProxy(ItemInfo("torch-1", "torch", "a torch"), picker)

    def test_a_proxy_looks_like_an_item_lying_on_the_ground(self):
        self.assertIsInstance(self.proxy, Item)              # it fits wherever an Item does
        self.assertEqual(("torch-1", "torch", "a torch"),
                         (self.proxy.item_id, self.proxy.name, self.proxy.describe()))
        self.assertEqual(("owned", "universe"), (self.proxy.state(), self.proxy.holder()))

    def test_pick_hands_the_question_to_the_picker(self):
        self.proxy.pick("ada")
        self.assertEqual([("torch-1", "ada")], self.calls)

    def test_a_pick_in_flight_cannot_begin_again(self):
        self.assertIsNone(self.proxy.begin_pick())
        self.assertIsNotNone(self.proxy.begin_pick())
        self.assertIsNone(self.proxy.cancel_pick())          # the Universe said no
        self.assertEqual("owned", self.proxy.state())


if __name__ == "__main__":
    unittest.main()