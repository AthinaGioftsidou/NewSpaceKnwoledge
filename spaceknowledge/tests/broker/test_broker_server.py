"""Unit tests for broker/broker_server.py: the Broker on its own thread."""

import threading
import unittest

from spaceknowledge.broker.broker import Broker
from spaceknowledge.broker.broker_server import BrokerServer
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.channel import InMemoryChannel, UniverseChannel
from spaceknowledge.transport.work_queue import ServerStoppedError


class TickingClock:
    """A pretend clock: every reading is 10 ms after the last, so tests never sleep."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 0.010
        return self.now


class TroubledChannel(UniverseChannel):
    """Passes requests on, unless told to act unreachable or to crash."""

    def __init__(self, inner):
        self.inner, self.trouble = inner, None

    def send(self, request):
        if self.trouble == "unreachable":
            raise ConnectionError("no route to the Universe")
        if self.trouble == "bug" and request.action == "mine":
            raise RuntimeError("a bug in the code")
        return self.inner.send(request)


class TestBrokerServer(unittest.TestCase):

    def setUp(self):
        self.channel = TroubledChannel(InMemoryChannel(a_universe()))
        self.broker = Broker(self.channel)
        self.server = BrokerServer(self.broker, clock=TickingClock())
        self.server.start()
        self.addCleanup(self.server.stop)          # always stop: the thread is not a daemon

    def test_a_server_that_was_never_started_takes_no_lines(self):
        idle = BrokerServer(Broker(InMemoryChannel(a_universe())))
        with self.assertRaises(ServerStoppedError):
            idle.submit("ada", "look")

    def test_join_then_play_by_typing(self):
        self.assertEqual("", self.server.join("ada", "earth"))          # "" means all is well
        self.assertEqual("You are at Earth.", self.server.submit("ada", "where"))
        self.assertTrue(self.server.join("bob", "pluto").startswith("Refused:"))

    def test_many_players_at_once_are_served_one_line_at_a_time(self):
        self.server.join("ada", "earth")
        replies = []
        threads = [threading.Thread(target=lambda: replies.append(
            self.server.submit("ada", "mine iron 1"))) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(["You mine 1 iron."] * 20, replies)
        self.assertEqual(20, self.broker.resources_of("ada").amount_of("iron"))   # none lost

    def test_an_unreachable_universe_becomes_a_reply_not_a_crash(self):
        self.server.join("ada", "earth")
        self.channel.trouble = "unreachable"
        reply = self.server.submit("ada", "mine iron 5")
        self.assertIn("the Universe did not answer", reply)
        self.assertEqual(1, self.server.stats()["requests_lost_connection"])

    def test_a_bug_reaches_the_caller_and_the_thread_survives(self):
        self.server.join("ada", "earth")
        self.channel.trouble = "bug"
        with self.assertRaisesRegex(RuntimeError, "a bug in the code"):
            self.server.submit("ada", "mine iron 5")
        self.channel.trouble = None
        self.assertEqual("You are at Earth.", self.server.submit("ada", "where"))
        self.assertEqual(1, self.server.stats()["requests_failed"])

    def test_stats_show_what_the_admin_needs(self):
        self.server.join("ada", "earth")
        self.server.submit("ada", "where")
        stats = self.server.stats()
        self.assertEqual(2, stats["requests_served"])
        self.assertEqual(0, stats["queue_depth"])
        self.assertTrue(stats["broker_thread_running"])
        self.assertEqual(10.0, stats["latency_ms"]["mean"])           # the ticking clock

    def test_after_stop_no_more_lines_are_taken(self):
        self.server.stop()
        self.assertFalse(self.server.is_running())
        with self.assertRaises(ServerStoppedError):
            self.server.submit("ada", "look")


if __name__ == "__main__":
    unittest.main()