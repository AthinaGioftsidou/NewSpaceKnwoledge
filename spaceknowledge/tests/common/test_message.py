"""Unit tests for common/messages.py."""

import unittest

from spaceknowledge.common.messages import ItemInfo, Request, Response
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


if __name__ == "__main__":
    unittest.main()