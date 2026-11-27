"""Unit tests for broker_web/http_protocol.py: the checks at the door."""

import unittest

from spaceknowledge.common.refusal import Refusal
from spaceknowledge.broker_web.http_protocol import (
    HttpProblem, bearer_token, only_fields, parse_json_body, refusal_body, scrub, text_field,
)


class TestHttpProtocol(unittest.TestCase):

    def assert_status(self, status, action):
        """`action` must be refused with this HTTP status."""
        with self.assertRaises(HttpProblem) as caught:
            action()
        self.assertEqual(status, caught.exception.status)

    def test_the_internal_server_is_never_named(self):
        self.assertEqual("the game world did not answer", scrub("the Universe did not answer"))
        body = refusal_body(Refusal("mine", "the UNIVERSE is busy", "ask the universe later"))
        self.assertEqual({"ok": False, "refusal": {"what": "mine", "why": "the game world is busy",
                                                    "next_step": "ask the game world later"}}, body)

    def test_a_body_must_be_a_json_object(self):
        self.assertEqual({"line": "look"}, parse_json_body(b'{"line": "look"}', "application/json"))
        self.assert_status(415, lambda: parse_json_body(b'{"line": "look"}', "text/plain"))
        self.assert_status(400, lambda: parse_json_body(b"{ broken", "application/json"))
        self.assert_status(400, lambda: parse_json_body(b"[1, 2]", "application/json"))

    def test_an_unknown_field_is_refused(self):
        only_fields({"line": "look"}, {"line"})                       # fine
        self.assert_status(400, lambda: only_fields({"line": "look", "admin": True}, {"line"}))

    def test_a_text_field_must_be_short_plain_text(self):
        self.assertEqual("look", text_field({"line": "look"}, "line", 200))
        self.assert_status(400, lambda: text_field({}, "line", 200))             # missing
        self.assert_status(400, lambda: text_field({"line": 5}, "line", 200))    # not text
        self.assert_status(400, lambda: text_field({"line": "x" * 201}, "line", 200))
        self.assert_status(400, lambda: text_field({"line": "lo\nok"}, "line", 200))
        self.assertEqual("pa\tss", text_field({"p": "pa\tss"}, "p", 200, allow_control=True))

    def test_the_token_comes_from_a_bearer_header(self):
        self.assertEqual("abc123", bearer_token("Bearer abc123"))
        for header in (None, "", "abc123", "Basic abc123", "Bearer ", "Bearer " + "x" * 129):
            with self.subTest(header=header):
                self.assert_status(401, lambda: bearer_token(header))


if __name__ == "__main__":
    unittest.main()