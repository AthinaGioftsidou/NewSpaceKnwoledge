"""Unit tests for broker/universe_proxy.py and broker/broker.py, with a real
Universe built from data/space.json behind an in-memory channel."""

import unittest

from spaceknowledge.broker.broker import Broker
from spaceknowledge.broker.inventory_repository import InMemoryInventoryRepository
from spaceknowledge.broker.pending_repository import InMemoryPendingRepository
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.channel import InMemoryChannel, UniverseChannel


class LosingChannel(UniverseChannel):
    """Delivers to the Universe, but when `lose` is set, the ANSWER is lost on
    the way back, the way a crash or a cut cable would lose it. `lose` can
    also be an action name, to lose only the answers to that action."""

    def __init__(self, inner):
        self.inner, self.lose = inner, False

    def send(self, request):
        response = self.inner.send(request)
        if self.lose is True or self.lose == request.action:
            raise ConnectionError("the answer was lost")
        return response

class FailingRepository(InMemoryInventoryRepository):
    """Saves normally until `fail` is set, then refuses like a full disk."""

    fail = False

    def save(self, *args, **kwargs):
        if self.fail:
            raise OSError("disk full")
        super().save(*args, **kwargs)



class FailingNotebook(InMemoryPendingRepository):
    """pending.json: saves normally until `fail` is set. `fail_after` lets a
    number of saves through first, to cut the power at an exact moment."""

    fail = False
    fail_after = None

    def save(self, pending):
        if self.fail_after is not None:
            if self.fail_after == 0:
                raise OSError("the power went out")
            self.fail_after -= 1
        if self.fail:
            raise OSError("disk full")
        super().save(pending)


class TestBroker(unittest.TestCase):

    def setUp(self):
        self.universe = a_universe()
        self.channel = LosingChannel(InMemoryChannel(self.universe))
        self.repository = FailingRepository()
        self.notebook = FailingNotebook()
        self.broker = Broker(self.channel, self.repository, self.notebook)
        self.broker.join("ada", "earth")

    def carried(self, broker=None):
        return [entry.name for entry in (broker or self.broker).inventory_of("ada").entries()]

    def test_a_new_player_starts_with_a_torch_once(self):
        self.assertEqual(["torch"], self.carried())
        self.assertTrue(self.broker.inventory_of("ada").entries()[0].item_id.startswith("torch-"))
        self.broker.join("ada", "earth")                 # logging in again
        self.assertEqual(["torch"], self.carried())

    def test_the_bag_grows_only_when_the_universe_says_yes(self):
        self.assertIsNone(self.broker.mine("ada", "iron", 5))
        self.assertIsNotNone(self.broker.mine("ada", "iron", 9999))
        self.assertEqual({"iron": 5}, self.broker.resources_of("ada").snapshot())

    def test_drop_then_pick_up_again(self):
        self.assertIsNone(self.broker.drop("ada", "torch"))
        self.assertEqual([], self.carried())
        self.assertEqual(["torch"], [proxy.name for proxy in self.broker.look("ada")])
        self.assertIsNone(self.broker.pick("ada", "torch"))
        self.assertEqual(["torch"], self.carried())
        self.assertEqual([], self.broker.look("ada"))

    def test_what_is_not_there_is_refused(self):
        self.assertEqual("you are not carrying lamp", self.broker.drop("ada", "lamp").why)
        self.assertIn("no lamp on the ground", self.broker.pick("ada", "lamp").why)
        self.assertIn("does not know a player called bob", self.broker.look("bob").why)

    def test_where_fly_and_the_mission_go_through_the_universe(self):
        self.assertEqual(("earth", "Earth"), self.broker.where("ada"))
        self.assertIn("launch gate is locked", self.broker.fly("ada", "Mars").why)
        self.broker.mine("ada", "iron", 20)
        self.assertEqual("question", self.broker.mission("ada").item_id)
        self.assertEqual("complete", self.broker.answer("ada", "  rust  ").item_id)
        self.assertEqual("Mars", self.broker.fly("ada", "mars").name)

    def test_nothing_stays_pending_after_an_answer(self):
        self.broker.mine("ada", "iron", 1)
        self.broker.drop("ada", "torch")
        self.assertEqual(0, self.broker.pending_count())

    def test_a_lost_answer_is_recovered_and_done_only_once(self):
        self.channel.lose = True
        with self.assertRaises(ConnectionError):
            self.broker.mine("ada", "iron", 5)           # mined, but the answer never came back
        self.assertEqual(1, self.broker.pending_count())
        self.assertEqual({}, self.broker.resources_of("ada").snapshot())
        # The Broker restarts: same saved file, fresh objects, a working line.
        self.channel.lose = False
        restarted = Broker(self.channel, self.repository, self.notebook)
        self.assertEqual(1, restarted.recover())         # the same op_id is sent again
        self.assertEqual({"iron": 5}, restarted.resources_of("ada").snapshot())
        self.assertEqual(0, restarted.pending_count())
        self.assertIn("only 495 iron left", restarted.mine("ada", "iron", 9999).why)  # mined ONCE

    def test_a_drop_whose_answer_was_lost_stays_locked_until_recovered(self):
        self.channel.lose = True
        with self.assertRaises(ConnectionError):
            self.broker.drop("ada", "torch")
        self.channel.lose = False
        restarted = Broker(self.channel, self.repository, self.notebook)
        self.assertEqual("flight", restarted.inventory_of("ada").entries()[0].state())
        restarted.recover()
        self.assertEqual([], self.carried(restarted))    # the drop was finished

    def test_if_the_intention_cannot_be_saved_nothing_is_sent(self):
        self.notebook.fail = True
        with self.assertRaises(OSError):
            self.broker.drop("ada", "torch")
        self.notebook.fail = False
        self.assertEqual("owned", self.broker.inventory_of("ada").entries()[0].state())  # undone
        self.assertEqual([], self.broker.look("ada"))    # the Universe never heard of it
        self.assertEqual(0, self.broker.pending_count())

    def test_the_notebook_lists_only_what_is_in_flight(self):
        self.channel.lose = True
        with self.assertRaises(ConnectionError):
            self.broker.drop("ada", "torch")
        in_flight = self.notebook.load()
        self.assertEqual(["add_item"], [r.action for r in in_flight])
        self.assertNotIn(in_flight[0].op_id, self.repository.load_settled())   # not applied yet

    def test_a_pick_in_flight_is_put_back_in_flight_after_a_power_cut(self):
        self.broker.drop("ada", "torch")
        self.channel.lose = "pick"
        with self.assertRaises(ConnectionError):
            self.broker.pick("ada", "torch")             # the torch is in flight...
        self.channel.lose = False
        restarted = Broker(self.channel, self.repository, self.notebook)   # ...power comes back
        self.assertEqual(["flight"], restarted.picks_in_flight())          # flight state restored
        self.assertEqual(1, restarted.recover())
        self.assertEqual([], restarted.picks_in_flight())
        self.assertEqual(["torch"], self.carried(restarted))

    def test_a_power_cut_between_the_two_saves_does_nothing_twice(self):
        # The answer is applied and players.json saved, then the power goes
        # out before pending.json is updated: the op_id is now in BOTH files.
        self.notebook.fail_after = 1                     # the intention is saved, then nothing
        with self.assertRaises(OSError):
            self.broker.mine("ada", "iron", 5)
        self.notebook.fail_after = None
        self.assertEqual(1, len(self.notebook.load()))   # still in pending.json
        self.assertEqual(1, len(self.repository.load_settled()))   # but marked settled
        restarted = Broker(self.channel, self.repository, self.notebook)
        self.assertEqual(0, restarted.pending_count())   # compared and crossed off
        self.assertEqual([], self.notebook.load())
        self.assertEqual({"iron": 5}, restarted.resources_of("ada").snapshot())   # not 10
        self.assertEqual(0, restarted.recover())         # nothing to send again

    def test_a_notebook_naming_a_stranger_is_refused(self):
        from spaceknowledge.broker.inventory_repository import CorruptStoreError
        from spaceknowledge.common.messages import Request
        self.notebook.save([Request("x-op1", "mine", "eve", "iron", 1)])
        with self.assertRaises(CorruptStoreError):
            Broker(self.channel, self.repository, self.notebook)


if __name__ == "__main__":
    unittest.main()