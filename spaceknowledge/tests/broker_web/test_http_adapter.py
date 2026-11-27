"""Unit tests for broker_web/http_adapter.py and broker_web/admin_routes.py, over real HTTP."""

import unittest
from unittest import mock

from spaceknowledge.tests.app.helpers import PASSWORD
from spaceknowledge.tests.broker_web.web_helpers import a_broker_web, call


class TestBrokerWeb(unittest.TestCase):

    def setUp(self):
        self.web, self.front, self.mailbox = a_broker_web(self)

    def sign_up(self, name="ada"):
        call(self.web, "POST", "/register", {"username": name, "password": PASSWORD})
        return call(self.web, "POST", "/login", {"username": name, "password": PASSWORD})[1]["token"]

    def test_the_page_is_served_with_safety_headers(self):
        status, _, headers = call(self.web, "GET", "/")
        self.assertEqual(200, status)
        self.assertEqual("DENY", headers["X-Frame-Options"])
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("X-Request-Id", headers)

    def test_register_log_in_play_log_out(self):
        status, body, _ = call(self.web, "POST", "/register", {"username": "ada", "password": PASSWORD})
        self.assertEqual((201, {"ok": True}), (status, body))
        token = call(self.web, "POST", "/login", {"username": "ada", "password": PASSWORD})[1]["token"]
        status, body, _ = call(self.web, "POST", "/command", {"line": "where"}, token=token)
        self.assertEqual((200, "You are at Earth."), (status, body["reply"]))
        status, body, _ = call(self.web, "POST", "/logout", {}, token=token)
        self.assertEqual((200, True), (status, body["was_logged_in"]))

    def test_a_refusal_by_the_game_is_still_a_good_request(self):
        status, body, _ = call(self.web, "POST", "/command", {"line": "dance"}, token=self.sign_up())
        self.assertEqual(200, status)
        self.assertTrue(body["reply"].startswith("Refused: dance."))

    def test_bad_requests_get_the_right_number(self):
        token = self.sign_up()
        cases = [
            (401, dict(body={"line": "where"})),                                    # no token
            (401, dict(body={"username": "ada", "password": "wrong password"}, path="/login")),
            (415, dict(raw=b'{"line": "where"}', headers={"Content-Type": "text/plain"})),
            (400, dict(raw=b"{ broken", headers={"Content-Type": "application/json"})),
            (400, dict(body={"line": "where", "admin": True})),                     # extra field
            (404, dict(body={}, path="/teleport")),
        ]
        for status, request in cases:
            with self.subTest(status=status, request=request):
                path = request.pop("path", "/command")
                use_token = None if status == 401 else token
                got, body, _ = call(self.web, "POST", path, token=use_token, **request)
                self.assertEqual(status, got)
                self.assertFalse(body["ok"])

    def test_a_huge_body_is_refused_before_it_is_read(self):
        status, _, _ = call(self.web, "POST", "/command", raw=b"x",
                            headers={"Content-Type": "application/json", "Content-Length": "999999"})
        self.assertEqual(413, status)

    def test_inside_trouble_never_leaks_out(self):
        token = self.sign_up()
        for error, status in ((RuntimeError("secret detail"), 500), (OSError("10.0.0.7 refused"), 503)):
            with self.subTest(status=status), mock.patch.object(self.front, "command", side_effect=error):
                got, body, _ = call(self.web, "POST", "/command", {"line": "where"}, token=token)
                self.assertEqual(status, got)
                self.assertNotIn("secret", str(body))
                self.assertNotIn("10.0.0.7", str(body))


class TestAdminRoutes(unittest.TestCase):

    def setUp(self):
        self.web, self.front, self.mailbox = a_broker_web(self)

    def test_an_admin_logs_in_with_a_code_and_reads(self):
        self.assertEqual((202, {"ok": True}), call(self.web, "POST", "/admin/code", {"admin": "root"})[:2])
        code = self.mailbox.messages[-1][1]
        token = call(self.web, "POST", "/admin/login", {"admin": "root", "code": code})[1]["token"]
        self.assertEqual([], call(self.web, "POST", "/admin/players", {}, token=token)[1]["players"])
        self.assertEqual("broker-1", call(self.web, "POST", "/admin/stats", {}, token=token)[1]["stats"]["broker"])

    def test_asking_for_a_code_says_the_same_for_anyone(self):
        known = call(self.web, "POST", "/admin/code", {"admin": "root"})[:2]
        unknown = call(self.web, "POST", "/admin/code", {"admin": "mallory"})[:2]
        self.assertEqual(known, unknown)

    def test_a_player_token_cannot_open_the_admin_door(self):
        call(self.web, "POST", "/register", {"username": "root", "password": PASSWORD})
        player = call(self.web, "POST", "/login", {"username": "root", "password": PASSWORD})[1]["token"]
        self.assertEqual(401, call(self.web, "POST", "/admin/players", {}, token=player)[0])


if __name__ == "__main__":
    unittest.main()