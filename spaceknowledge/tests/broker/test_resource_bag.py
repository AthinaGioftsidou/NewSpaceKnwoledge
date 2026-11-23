"""Unit tests for broker/resource_bag.py."""

import unittest

from spaceknowledge.broker.resource_bag import ResourceBag


class TestResourceBag(unittest.TestCase):

    def setUp(self):
        self.bag = ResourceBag()

    def test_a_new_bag_is_empty(self):
        self.assertTrue(self.bag.is_empty())
        self.assertEqual(0, self.bag.amount_of("iron"))

    def test_amounts_add_up(self):
        self.bag.add("iron", 5)
        self.bag.add("iron", 15)
        self.bag.add("wood", 2)
        self.assertEqual(20, self.bag.amount_of("iron"))
        self.assertEqual({"iron": 20, "wood": 2}, self.bag.snapshot())

    def test_only_whole_amounts_of_at_least_one(self):
        with self.assertRaises(ValueError):
            self.bag.add("iron", 0)              # so the bag never stores a zero
        with self.assertRaises(TypeError):
            self.bag.add("iron", True)
        self.assertTrue(self.bag.is_empty())

    def test_snapshot_is_a_copy(self):
        self.bag.add("iron", 5)
        self.bag.snapshot()["iron"] = 999
        self.assertEqual(5, self.bag.amount_of("iron"))


if __name__ == "__main__":
    unittest.main()