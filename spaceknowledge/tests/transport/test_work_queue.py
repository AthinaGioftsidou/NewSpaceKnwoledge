"""Unit tests for transport/work_queue.py."""

import threading
import unittest

from spaceknowledge.transport.work_queue import ServerStoppedError, Ticket, WorkQueue


class TestWorkQueue(unittest.TestCase):

    def setUp(self):
        self.queue = WorkQueue()

    def test_first_in_first_out(self):
        for word in ("a", "b", "c"):
            self.queue.push(word)
        self.assertEqual(["a", "b", "c"], [self.queue.pop() for _ in range(3)])

    def test_pop_waits_until_work_arrives(self):
        got = []
        worker = threading.Thread(target=lambda: got.append(self.queue.pop()))
        worker.start()                      # it waits: the queue is empty
        self.queue.push("job")              # this wakes it up
        worker.join(timeout=2)
        self.assertEqual(["job"], got)

    def test_a_closed_queue_finishes_its_work_then_says_none(self):
        self.queue.push("last job")
        self.queue.close()
        self.assertEqual("last job", self.queue.pop())   # queued work is still served
        self.assertIsNone(self.queue.pop())              # then: nothing more, ever
        with self.assertRaises(ServerStoppedError):
            self.queue.push("too late")

    def test_server_stopped_is_a_kind_of_connection_error(self):
        self.assertTrue(issubclass(ServerStoppedError, ConnectionError))


class TestTicket(unittest.TestCase):

    def test_wait_returns_the_answer(self):
        ticket = Ticket("question")
        ticket.complete("answer")
        self.assertEqual("answer", ticket.wait(timeout=1))

    def test_wait_raises_the_workers_error(self):
        ticket = Ticket("question")
        ticket.fail(RuntimeError("it broke"))
        with self.assertRaisesRegex(RuntimeError, "it broke"):
            ticket.wait(timeout=1)

    def test_no_answer_in_time_is_a_timeout(self):
        with self.assertRaises(TimeoutError):
            Ticket("question").wait(timeout=0.01)


if __name__ == "__main__":
    unittest.main()