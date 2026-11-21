"""Unit tests for common/item_cycle.py."""

import unittest

from spaceknowledge.common.item_cycle import (
    BROKER, DONE, DROP, FLIGHT, OWNED, PICK, UNIVERSE, ItemCycle, Process,
)


class TestItemCycle(unittest.TestCase):

    def setUp(self):
        # Runs before EVERY test: a torch in the player's hand.
        self.torch = ItemCycle("torch")

    def test_new_item_is_owned_by_the_broker_and_usable(self):
        self.assertEqual("drop", self.torch.process_name())
        self.assertEqual(OWNED, self.torch.state())
        self.assertEqual(BROKER, self.torch.holder())
        self.assertTrue(self.torch.is_usable())

    def test_a_drop_goes_owned_flight_done(self):
        self.assertIsNone(self.torch.begin(DROP))
        self.assertEqual(FLIGHT, self.torch.state())
        self.assertFalse(self.torch.is_usable())          # locked while waiting
        self.assertIsNone(self.torch.finish(DROP))
        self.assertEqual(DONE, self.torch.state())
        self.assertEqual(UNIVERSE, self.torch.holder())   # now on the ground

    def test_cannot_drop_twice_while_in_flight(self):
        self.torch.begin(DROP)
        refusal = self.torch.begin(DROP)
        self.assertIsNotNone(refusal)
        self.assertEqual(FLIGHT, self.torch.state())      # nothing changed
        self.assertIn("wait", refusal.next_step)

    def test_cancel_makes_the_item_usable_again(self):
        self.torch.begin(DROP)
        self.assertIsNone(self.torch.cancel(DROP))        # the Universe said no
        self.assertEqual(OWNED, self.torch.state())
        self.assertTrue(self.torch.is_usable())

    def test_a_finished_drop_rolls_over_to_a_pick(self):
        self.torch.begin(DROP)
        self.torch.finish(DROP)
        self.assertIsNone(self.torch.begin(PICK))
        self.assertEqual("pick", self.torch.process_name())
        self.assertEqual(FLIGHT, self.torch.state())

    def test_the_wrong_process_is_refused_and_changes_nothing(self):
        on_ground = ItemCycle("torch", PICK)
        refusal = on_ground.begin(DROP)                   # you cannot drop what lies on the ground
        self.assertIsNotNone(refusal)
        self.assertEqual("pick", on_ground.process_name())
        self.assertEqual(OWNED, on_ground.state())
        self.assertIn("pick it up", refusal.next_step)

    def test_a_process_needs_a_known_holder(self):
        with self.assertRaises(ValueError):
            Process("drop", "drop", BROKER, "nobody", UNIVERSE, "advice", "advice")


if __name__ == "__main__":
    unittest.main()