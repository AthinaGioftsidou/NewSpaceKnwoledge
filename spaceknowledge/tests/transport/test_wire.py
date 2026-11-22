"""Unit tests for transport/wire.py."""

import io
import json
import unittest

from spaceknowledge.common.messages import ItemInfo, Request, Response
from spaceknowledge.common.refusal import Refusal
from spaceknowledge.transport.wire import (
    MAX_LINE, WireError, read_message, request_from_wire, request_to_wire,
    response_from_wire, response_to_wire, write_message,
)


def through_the_wire(*messages):
    """Write messages as bytes, then give back a stream to read them from,
    the way the other side of a connection would."""
    sent = []                                   # stands in for sock.sendall
    for message in messages:
        write_message(sent.append, message)
    return io.BytesIO(b"".join(sent))


class TestWire(unittest.TestCase):

    def test_one_message_is_one_line(self):
        sent = []
        write_message(sent.append, {"text": "line one\nline two"})
        self.assertEqual(b'{"text":"line one\\nline two"}\n', sent[0])   # the newline is escaped

    def test_a_request_survives_the_trip(self):
        request = Request("op1", "add_item", "ada", "torch-1", 1, "torch")
        stream = through_the_wire(request_to_wire(request))
        back = request_from_wire(read_message(stream))
        self.assertEqual(("op1", "add_item", "ada", "torch-1", 1, "torch"),
                         (back.op_id, back.action, back.player_id, back.item_id,
                          back.amount, back.name))

    def test_both_kinds_of_response_survive_the_trip(self):
        ok = Response("op1", items=(ItemInfo("earth", "Earth", "Home."),))
        no = Response("op2", Refusal("fly mars", "the way is shut", "finish the mission"))
        stream = through_the_wire(response_to_wire(ok), response_to_wire(no))
        self.assertEqual("Earth", response_from_wire(read_message(stream)).items[0].name)
        self.assertEqual("the way is shut", response_from_wire(read_message(stream)).refusal.why)
        self.assertIsNone(read_message(stream))      # the end of the stream

    def test_broken_lines_are_refused(self):
        for raw in (b"this is not json\n",
                    b'["a list, not an object"]\n',
                    b'{"cut": "off"',                        # no newline at the end
                    b"x" * (MAX_LINE + 10) + b"\n"):        # far too long
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(WireError):
                    read_message(io.BytesIO(raw))

    def test_a_request_with_a_missing_or_unknown_field_is_refused(self):
        good = request_to_wire(Request("op1", "look", "ada", "here"))
        missing = {k: v for k, v in good.items() if k != "player_id"}
        for body in (missing, {**good, "admin": True}, {**good, "amount": True}):
            with self.subTest(body=body):
                with self.assertRaises(WireError):
                    request_from_wire(body)

    def test_a_response_whose_ok_and_refusal_disagree_is_refused(self):
        with self.assertRaises(WireError):
            response_from_wire({"op_id": "op1", "ok": True,
                                "refusal": {"what": "a", "why": "b", "next_step": "c"}})


if __name__ == "__main__":
    unittest.main()