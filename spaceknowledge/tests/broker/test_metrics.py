"""Unit tests for broker/metrics.py."""

import unittest

from spaceknowledge.broker.metrics import BrokerMetrics


class TestBrokerMetrics(unittest.TestCase):

    def test_a_new_broker_has_done_nothing(self):
        snapshot = BrokerMetrics().snapshot()
        self.assertEqual(0, snapshot["requests_served"])
        self.assertEqual({"count": 0, "mean": 0.0, "max": 0.0, "p95": 0.0}, snapshot["latency_ms"])

    def test_outcomes_are_counted_and_latency_is_measured(self):
        metrics = BrokerMetrics()
        for ms in range(1, 101):                  # 1 ms, 2 ms, ... 100 ms
            metrics.record(ms, "served")
        metrics.record(50, "lost")
        snapshot = metrics.snapshot()
        self.assertEqual((100, 1, 0), (snapshot["requests_served"],
                                       snapshot["requests_lost_connection"],
                                       snapshot["requests_failed"]))
        self.assertEqual(101, snapshot["latency_ms"]["count"])
        self.assertEqual(100.0, snapshot["latency_ms"]["max"])
        self.assertEqual(95.0, snapshot["latency_ms"]["p95"])

    def test_the_95th_percentile_only_looks_at_recent_requests(self):
        metrics = BrokerMetrics(window=3)
        for ms in (500, 2, 2, 2):                 # one slow request long ago
            metrics.record(ms, "served")
        latency = metrics.snapshot()["latency_ms"]
        self.assertEqual(500.0, latency["max"])   # the max remembers everything...
        self.assertEqual(2.0, latency["p95"])     # ...the p95 only the last 3

    def test_bad_numbers_are_refused(self):
        metrics = BrokerMetrics()
        with self.assertRaises(ValueError):
            metrics.record(5, "teleported")
        with self.assertRaises(ValueError):
            metrics.record(-1, "served")
        with self.assertRaises(ValueError):
            metrics.set_pending(True)


if __name__ == "__main__":
    unittest.main()