"""Unit tests for users/session_book.py."""

import unittest

from spaceknowledge.tests.users.fake_clock import FakeClock
from spaceknowledge.users.session_book import SessionBook


class TestSessionBook(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock()
        self.book = SessionBook(clock=self.clock, lifetime=3600, idle_timeout=600)
        self.token = self.book.open("ada")

    def test_a_token_stands_for_one_player(self):
        self.assertEqual("ada", self.book.player_for(self.token))
        self.assertGreaterEqual(len(self.token), 32)
        self.assertNotEqual(self.token, self.book.open("ada"))   # every login a new token
        self.assertIsNone(self.book.player_for("made-up-token"))

    def test_a_token_left_unused_runs_out(self):
        self.clock.advance(599)
        self.assertEqual("ada", self.book.player_for(self.token))   # used: idle time restarts
        self.clock.advance(599)
        self.assertEqual("ada", self.book.player_for(self.token))
        self.clock.advance(600)
        self.assertIsNone(self.book.player_for(self.token))        # 10 minutes untouched

    def test_no_token_lives_longer_than_its_lifetime(self):
        for _ in range(7):                                         # busy all the time...
            self.clock.advance(500)
            self.assertEqual("ada", self.book.player_for(self.token))
        self.clock.advance(100)                                    # ...but 3600 s have passed
        self.assertIsNone(self.book.player_for(self.token))

    def test_logging_out_ends_the_token(self):
        self.assertTrue(self.book.close(self.token))
        self.assertIsNone(self.book.player_for(self.token))
        self.assertFalse(self.book.close(self.token))              # nothing left to close

    def test_closing_an_expired_token_says_it_was_not_live(self):
        self.clock.advance(601)
        self.assertFalse(self.book.close(self.token))

    def test_expired_tokens_are_cleared_away(self):
        self.clock.advance(601)
        self.book.open("bob")                                      # opening tidies up
        self.assertEqual(1, self.book.count())

    def test_a_token_must_be_text(self):
        with self.assertRaises(TypeError):
            self.book.player_for(12345)


if __name__ == "__main__":
    unittest.main()