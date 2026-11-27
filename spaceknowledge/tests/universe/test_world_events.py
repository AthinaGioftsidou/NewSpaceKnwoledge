"""Unit tests for universe/world_events.py, and for the Universe as the
Observer's subject: who is told what, and when."""

import unittest
from itertools import count

from spaceknowledge.common.messages import Request, WorldEvent
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.universe.world_events import (
    MAX_EVENTS_PER_ANSWER, EventFeed, EventLogger, WorldObserver,
)


class Recorder(WorldObserver):
    """A test observer: it only writes down what it is told."""

    def __init__(self):
        self.heard = []

    def notify(self, event):
        self.heard.append(event.describe())


def an_event(seq, place="earth", player="ada", action="drop", item="torch"):
    return WorldEvent(seq, place, player, action, item)


class TestEventFeed(unittest.TestCase):

    def test_it_gives_the_news_of_one_place_without_your_own(self):
        feed = EventFeed()
        for event in (an_event(1), an_event(2, player="bob"), an_event(3, place="mars")):
            feed.notify(event)
        self.assertEqual(["bob dropped a torch"],
                         [e.describe() for e in feed.since(0, "earth", "ada")])
        self.assertEqual([1, 2], [e.seq for e in feed.since(0, "earth", "eve")])
        self.assertEqual([2], [e.seq for e in feed.since(1, "earth", "eve")])   # only newer

    def test_it_keeps_only_the_newest(self):
        feed = EventFeed(keep=3)
        for seq in range(1, 6):
            feed.notify(an_event(seq))
        self.assertEqual(3, feed.count())
        self.assertEqual([3, 4, 5], [e.seq for e in feed.since(0, "earth", "eve")])

    def test_one_answer_is_never_too_long(self):
        feed = EventFeed()
        for seq in range(1, 51):
            feed.notify(an_event(seq))
        news = feed.since(0, "earth", "eve")
        self.assertEqual(MAX_EVENTS_PER_ANSWER, len(news))
        self.assertEqual(50, news[-1].seq)                       # the newest are kept

    def test_the_logger_writes_every_event_to_the_log(self):
        with self.assertLogs("spaceknowledge.universe.world_events", "INFO") as logged:
            EventLogger().notify(an_event(7, action="pick"))
        self.assertIn("ada picked up a torch", logged.output[0])


class TestTheUniverseAsSubject(unittest.TestCase):

    def setUp(self):
        self.universe = a_universe()
        self.numbers = count(1)
        self.recorder = Recorder()
        self.universe.subscribe(self.recorder)
        for player in ("ada", "bob"):
            self.ask(player, "join", "earth")

    def ask(self, player, action, target, name=None, op_id=None):
        op_id = op_id or f"op{next(self.numbers)}"
        return self.universe.handle(Request(op_id, action, player, target, 1, name))

    def test_a_drop_and_a_pick_are_told_to_every_observer(self):
        self.ask("ada", "add_item", "torch-1", "torch")
        self.ask("bob", "pick", "torch-1")
        self.assertEqual(["ada dropped a torch", "bob picked up a torch"], self.recorder.heard)

    def test_a_refused_drop_tells_nobody(self):
        self.ask("ada", "add_item", "torch-1", "torch")
        self.ask("ada", "add_item", "torch-1", "torch")            # the same id again: refused
        self.ask("bob", "pick", "nothing-here")                     # refused too
        self.assertEqual(["ada dropped a torch"], self.recorder.heard)

    def test_a_repeated_request_is_not_news_twice(self):
        self.ask("ada", "add_item", "torch-1", "torch", op_id="x-op1")
        self.ask("ada", "add_item", "torch-1", "torch", op_id="x-op1")   # remembered answer
        self.assertEqual(1, len(self.recorder.heard))

    def test_an_unsubscribed_observer_hears_nothing_more(self):
        self.universe.unsubscribe(self.recorder)
        self.ask("ada", "add_item", "torch-1", "torch")
        self.assertEqual([], self.recorder.heard)

    def test_news_is_what_others_did_where_you_are(self):
        start = self.ask("bob", "news", "0").latest
        self.ask("ada", "add_item", "torch-1", "torch")
        news = self.ask("bob", "news", str(start))
        self.assertEqual(["ada dropped a torch"], [e.describe() for e in news.events])
        self.assertEqual(news.events[-1].seq, news.latest)
        self.assertEqual((), self.ask("ada", "news", str(start)).events)   # not your own
        self.assertEqual((), self.ask("bob", "news", str(news.latest)).events)  # seen already

    def test_news_from_another_place_is_not_shown(self):
        self.ask("ada", "add_item", "torch-1", "torch")
        self.universe.place_player("bob", "moon")
        self.assertEqual((), self.ask("bob", "news", "0").events)

    def test_a_bad_news_number_is_refused(self):
        for cursor in ("-1", "ten", "1" * 19):
            with self.subTest(cursor=cursor):
                self.assertFalse(self.ask("bob", "news", cursor).ok)

    def test_asking_for_news_changes_nothing_and_is_not_remembered(self):
        before = self.universe.answer_count()
        self.ask("bob", "news", "0")
        self.assertEqual(before, self.universe.answer_count())


if __name__ == "__main__":
    unittest.main()