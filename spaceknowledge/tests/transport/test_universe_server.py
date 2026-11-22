"""Unit tests for transport/channel.py, universe_server.py and threaded_channel.py."""

import threading
import unittest

from spaceknowledge.common.messages import Request
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.channel import InMemoryChannel
from spaceknowledge.transport.threaded_channel import ThreadedChannel
from spaceknowledge.transport.universe_server import UniverseServer
from spaceknowledge.transport.work_queue import ServerStoppedError
from spaceknowledge.universe.universe import Universe


class RecordingUniverse(Universe):
    """A real Universe that also notes which thread handled each request."""

    def __init__(self, *args, **kwargs):
        self.threads = []
        super().__init__(*args, **kwargs)

    def handle(self, request):
        self.threads.append(threading.current_thread().name)
        if request.action == "explode":
            raise RuntimeError("the Universe broke")
        return super().handle(request)


def a_recording_universe():
    plain = a_universe()
    return RecordingUniverse(plain._world, plain._deposits, missions=plain._missions)


class TestChannels(unittest.TestCase):

    def test_the_in_memory_channel_calls_the_universe_directly(self):
        channel = InMemoryChannel(a_universe())
        self.assertTrue(channel.send(Request("op1", "join", "ada", "earth")).ok)

    def test_a_server_that_was_never_started_takes_no_calls(self):
        server = UniverseServer(a_universe())
        with self.assertRaises(ServerStoppedError):
            server.call(Request("op1", "join", "ada", "earth"), timeout=1)


class TestUniverseServer(unittest.TestCase):

    def setUp(self):
        self.universe = a_recording_universe()
        self.server = UniverseServer(self.universe)
        self.server.start()
        self.addCleanup(self.server.stop)          # always stop: the thread is not a daemon
        self.channel = ThreadedChannel(self.server)

    def test_requests_are_answered_on_the_universe_thread(self):
        self.assertTrue(self.channel.send(Request("op1", "join", "ada", "earth")).ok)
        self.assertEqual("Earth", self.channel.send(Request("op2", "where", "ada", "here")).items[0].name)
        self.assertEqual(["universe", "universe"], self.universe.threads)

    def test_an_error_in_the_universe_reaches_the_caller(self):
        with self.assertRaisesRegex(RuntimeError, "the Universe broke"):
            self.channel.send(Request("op1", "explode", "ada", "here"))
        self.assertTrue(self.server.is_running())  # one bad request does not stop the thread

    def test_after_stop_no_more_calls_are_taken(self):
        self.server.stop()
        self.assertFalse(self.server.is_running())
        with self.assertRaises(ServerStoppedError):
            self.channel.send(Request("op1", "join", "ada", "earth"))


if __name__ == "__main__":
    unittest.main()