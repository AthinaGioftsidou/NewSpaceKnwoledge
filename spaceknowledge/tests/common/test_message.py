"""Unit tests for common/messages.py."""

import unittest

from spaceknowledge.common.messages import ItemInfo, News, Request, Response, WorldEvent
from spaceknowledge.common.refusal import Refusal


class TestMessages(unittest.TestCase):

    def test_request_defaults(self):
        request = Request("op1", "pick", "ada", "torch-1")
        self.assertEqual(1, request.amount)
        self.assertEqual("torch-1", request.display_name)  # no name, so the id is shown

    def test_true_is_not_accepted_as_an_amount(self):
        with self.assertRaises(TypeError):
            Request("op1", "mine", "ada", "iron", True)

    def test_response_without_refusal_is_ok(self):
        self.assertTrue(Response("op1").ok)
        refused = Response("op2", Refusal("mine gold", "no gold here", "mine something else"))
        self.assertFalse(refused.ok)

    def test_refusal_cannot_carry_items(self):
        refusal = Refusal("pick torch", "it is gone", "type look")
        with self.assertRaises(ValueError):
            Response("op1", refusal, (ItemInfo("t1", "torch", "a torch"),))

    def test_a_world_event_tells_what_happened(self):
        self.assertEqual("ada dropped a torch",
                         WorldEvent(1, "earth", "ada", "drop", "torch").describe())
        self.assertEqual("bob picked up a torch",
                         WorldEvent(2, "earth", "bob", "pick", "torch").describe())

    def test_a_bad_world_event_cannot_be_made(self):
        for args in ((0, "earth", "ada", "drop", "torch"),       # numbers start at 1
                     (True, "earth", "ada", "drop", "torch"),    # true is not a number
                     (1, "", "ada", "drop", "torch"),
                     (1, "earth", "ada", "dance", "torch")):     # not something to report
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    WorldEvent(*args)

    def test_news_and_a_refusal_never_travel_together(self):
        event = WorldEvent(1, "earth", "ada", "drop", "torch")
        self.assertEqual((event,), Response("op1", events=(event,), latest=1).events)
        with self.assertRaises(ValueError):
            Response("op1", Refusal("a", "b", "c"), events=(event,))
        with self.assertRaises(ValueError):
            News((), -1)


if __name__ == "__main__":
    unittest.main()