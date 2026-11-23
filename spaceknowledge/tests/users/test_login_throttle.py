"""Unit tests for users/login_throttle.py."""

import unittest

from spaceknowledge.tests.users.fake_clock import FakeClock
from spaceknowledge.users.login_throttle import LoginThrottle


class TestLoginThrottle(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock()
        self.throttle = LoginThrottle(clock=self.clock, max_failures=5, lockout=300)

    def fail(self, name, times):
        for _ in range(times):
            self.throttle.record_failure(name)

    def test_the_fifth_wrong_password_locks_the_name(self):
        self.fail("ada", 4)
        self.assertFalse(self.throttle.is_locked("ada"))
        self.fail("ada", 1)
        self.assertTrue(self.throttle.is_locked("ada"))
        self.assertFalse(self.throttle.is_locked("bob"))         # only that name

    def test_the_lock_ends_after_the_lockout(self):
        self.fail("ada", 5)
        self.clock.advance(299)
        self.assertTrue(self.throttle.is_locked("ada"))
        self.clock.advance(1)
        self.assertFalse(self.throttle.is_locked("ada"))
        self.assertEqual(0, self.throttle.tracked_count())       # and it is forgotten

    def test_more_failures_while_locked_do_not_extend_the_lock(self):
        self.fail("ada", 5)
        self.clock.advance(200)
        self.fail("ada", 10)                                     # still hammering
        self.clock.advance(100)
        self.assertFalse(self.throttle.is_locked("ada"))

    def test_a_success_wipes_the_count(self):
        self.fail("ada", 4)
        self.throttle.record_success("ada")
        self.fail("ada", 4)
        self.assertFalse(self.throttle.is_locked("ada"))

    def test_one_name_however_it_is_typed(self):
        self.fail("ADA", 3)
        self.fail("  ada ", 2)
        self.assertTrue(self.throttle.is_locked("Ada"))

    def test_it_never_remembers_more_than_it_may(self):
        small = LoginThrottle(clock=self.clock, max_tracked=2)
        for name in ("ada", "bob", "eve"):
            small.record_failure(name)
        self.assertEqual(2, small.tracked_count())               # the oldest was let go

    def test_bad_settings_are_refused(self):
        for settings in ({"max_failures": 0}, {"lockout": 0}, {"max_tracked": 0}):
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    LoginThrottle(**settings)


if __name__ == "__main__":
    unittest.main()