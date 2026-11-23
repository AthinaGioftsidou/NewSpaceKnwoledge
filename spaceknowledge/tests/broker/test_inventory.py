"""Unit tests for broker/inventory_entry.py and broker/player_inventory.py."""

import unittest

from spaceknowledge.broker.inventory_entry import InventoryEntry
from spaceknowledge.broker.player_inventory import PlayerInventory


class TestInventoryEntry(unittest.TestCase):

    def test_an_entry_goes_round_the_drop_cycle(self):
        torch = InventoryEntry("torch-1", "torch")
        self.assertTrue(torch.is_usable())
        self.assertIsNone(torch.begin_drop())
        self.assertEqual("flight", torch.state())
        self.assertFalse(torch.is_usable())          # locked while the Universe decides
        self.assertIsNone(torch.cancel_drop())       # the Universe said no
        self.assertTrue(torch.is_usable())


class TestPlayerInventory(unittest.TestCase):

    def setUp(self):
        self.inventory = PlayerInventory()
        self.inventory.add(InventoryEntry("torch-b", "torch"))
        self.inventory.add(InventoryEntry("torch-a", "Torch"))

    def test_two_entries_with_one_id_are_refused(self):
        with self.assertRaises(ValueError):
            self.inventory.add(InventoryEntry("torch-a", "lamp"))

    def test_resolve_by_id_or_by_name(self):
        self.assertEqual("torch-b", self.inventory.resolve("torch-b").item_id)
        # Two share the name: the first by id wins...
        self.assertEqual("torch-a", self.inventory.resolve("TORCH").item_id)
        # ...unless it is busy, then the first USABLE one wins.
        self.inventory.begin_drop("torch-a")
        self.assertEqual("torch-b", self.inventory.resolve("torch").item_id)
        self.assertIsNone(self.inventory.resolve("lamp"))

    def test_a_finished_drop_removes_the_entry(self):
        self.inventory.begin_drop("torch-a")
        self.assertIsNone(self.inventory.finish_drop("torch-a"))
        self.assertIsNone(self.inventory.find("torch-a"))
        self.assertEqual(1, self.inventory.count())

    def test_an_item_in_flight_cannot_be_used_or_dropped_again(self):
        self.inventory.begin_drop("torch-a")
        self.assertIn("cannot be used in state flight",
                      self.inventory.check_usable("torch-a").why)
        self.assertIsNotNone(self.inventory.begin_drop("torch-a"))

    def test_something_not_carried_gets_a_helpful_refusal(self):
        refusal = self.inventory.begin_drop("lamp-1")
        self.assertEqual("you are not carrying lamp-1", refusal.why)
        self.assertEqual("type inventory to see what you carry", refusal.next_step)


if __name__ == "__main__":
    unittest.main()