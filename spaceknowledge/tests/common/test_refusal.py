"""Unit tests for common/refusal.py."""

import unittest

from spaceknowledge.common.refusal import Refusal


class TestRefusal(unittest.TestCase):

    def test_describe_shows_what_why_and_next_step(self):
        refusal = Refusal("mine gold", "there is no gold here", "mine something else")
        self.assertEqual(
            "Refused: mine gold. Why: there is no gold here. Next: mine something else.",
            refusal.describe(),
        )

    def test_empty_text_is_not_allowed(self):
        with self.assertRaises(ValueError):
            Refusal("", "why", "next")

    def test_refusal_cannot_be_changed(self):
        refusal = Refusal("what", "why", "next")
        with self.assertRaises(AttributeError):
            refusal.why = "something else"


if __name__ == "__main__":
    unittest.main()