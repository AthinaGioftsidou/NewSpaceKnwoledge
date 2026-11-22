"""Unit tests for transport/call_queue.py."""

import unittest

from spaceknowledge.common.messages import Request, Response
from spaceknowledge.transport.call_queue import CallQueue, PendingCall


class TestCallQueue(unittest.TestCase):

    def test_a_pending_call_carries_a_request_and_answers_with_a_response(self):
        call = PendingCall(Request("op1", "look", "ada", "here"))
        self.assertEqual("look", call.request.action)
        call.complete(Response("op1"))
        self.assertTrue(call.wait(timeout=1).ok)

    def test_the_wrong_types_are_refused(self):
        with self.assertRaises(TypeError):
            PendingCall("look")                                    # not a Request
        with self.assertRaises(TypeError):
            PendingCall(Request("op1", "look", "ada", "here")).complete("ok")   # not a Response
        with self.assertRaises(TypeError):
            CallQueue().push("look")                               # not a PendingCall


if __name__ == "__main__":
    unittest.main()