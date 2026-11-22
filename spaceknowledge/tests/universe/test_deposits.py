"""Unit tests for universe/deposits.py."""

import unittest

from spaceknowledge.universe.deposits import Deposits


class TestDeposits(unittest.TestCase):

    def setUp(self):
        self.deposits = Deposits({"earth": {"iron": 500, "wood": 300}, "mars": {"nickel": 200}})

    def test_read_from_a_world_file(self):
        raw = {"destinations": [
            {"id": "earth", "resources": {"iron": 500}},
            {"id": "moon"},                                  # no resources: skipped
        ]}
        deposits = Deposits.from_raw(raw)
        self.assertEqual(500, deposits.available("earth", "iron"))
        self.assertEqual({"earth": {"iron": 500}}, deposits.snapshot())

    def test_what_is_not_there_is_zero(self):
        self.assertEqual(0, self.deposits.available("earth", "gold"))   # unknown resource
        self.assertEqual(0, self.deposits.available("pluto", "iron"))   # unknown place

    def test_remove_takes_from_the_stock(self):
        self.deposits.remove("earth", "iron", 20)
        self.assertEqual(480, self.deposits.available("earth", "iron"))

    def test_cannot_remove_more_than_is_left_or_less_than_one(self):
        with self.assertRaises(ValueError):
            self.deposits.remove("mars", "nickel", 201)
        with self.assertRaises(ValueError):
            self.deposits.remove("mars", "nickel", 0)
        self.assertEqual(200, self.deposits.available("mars", "nickel"))   # unchanged

    def test_a_bad_quantity_is_refused(self):
        for quantity in (-1, True, "10"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    Deposits({"earth": {"iron": quantity}})

    def test_snapshot_is_a_copy_and_a_bad_restore_changes_nothing(self):
        saved = self.deposits.snapshot()
        saved["earth"]["iron"] = 0                            # changing the copy...
        self.assertEqual(500, self.deposits.available("earth", "iron"))   # ...changes nothing
        with self.assertRaises(ValueError):
            self.deposits.restore({"earth": {"iron": -5}})
        self.assertEqual(500, self.deposits.available("earth", "iron"))


if __name__ == "__main__":
    unittest.main()