"""SIMULATION TESTS: many players typing random commands, then a check that
the game is still consistent.

The commands are random, but the random generator has a fixed seed, so every
run makes exactly the same choices: a failure can always be repeated. After
the players stop, the test checks the rules that must hold whatever happened:

    every item is in exactly one place: one pocket, or the ground of one place
    no item appeared or disappeared
    every unit of a resource is either in a player's bag or still in the ground
    nothing is left in flight: no pending operation, no item locked
    every command got an answer, and none was an inside error

One test plays the players one after another; the other lets them all type
at the same time, on their own threads, the way real clients do.
"""

import json
import random
import threading
import unittest

from spaceknowledge.app.front import Front
from spaceknowledge.broker.broker import Broker
from spaceknowledge.broker.broker_server import BrokerServer
from spaceknowledge.tests.app.helpers import PASSWORD
from spaceknowledge.tests.universe.test_universe import SPACE_FILE
from spaceknowledge.transport.channel import InMemoryChannel
from spaceknowledge.universe.deposits import Deposits
from spaceknowledge.universe.missions import MissionBook
from spaceknowledge.universe.universe import Universe
from spaceknowledge.users.accounts import AccountRegistry
from spaceknowledge.users.session_book import SessionBook
from spaceknowledge.world.loader import StandardWorldLoader

PLAYERS = ("ada", "bob", "eve", "max", "zoe")


def random_command(dice: random.Random) -> str:
    """One command, the kind a curious (or careless) player might type."""
    return dice.choice([
        "look", "where", "inventory", "mission", "help",
        "drop torch", "pick torch", "pick up the torch",
        f"mine iron {dice.randint(1, 30)}", f"mine wood {dice.randint(1, 50)}",
        f"mine nickel {dice.randint(1, 20)}", f"mine helium_3 {dice.randint(1, 10)}",
        "mine gold 1", "mine iron 0",
        "fly to earth", "fly to the moon", "fly to mars", "fly to pluto",
        "answer rust", "answer copper",
        "dance", "pick", "drop", "x" * 50,
    ])


class TestSimulation(unittest.TestCase):

    def setUp(self):
        raw = json.loads(SPACE_FILE.read_text(encoding="utf-8"))
        self.start_stock = Deposits.from_raw(raw).snapshot()
        self.world = StandardWorldLoader().build(raw)
        self.deposits = Deposits.from_raw(raw)
        universe = Universe(self.world, self.deposits, missions=MissionBook.from_raw(raw))
        self.broker = Broker(InMemoryChannel(universe))
        server = BrokerServer(self.broker)
        server.start()
        self.addCleanup(server.stop)
        self.front = Front(AccountRegistry(iterations=1), SessionBook(), server, "earth")
        self.tokens = {}
        for name in PLAYERS:
            self.front.register(name, PASSWORD)
            self.tokens[name] = self.front.login(name, PASSWORD)
        self.items_at_start = self.all_items()
        self.replies = []

    def all_items(self):
        """Every item id in the game, with a count of the places it is in."""
        places = []
        for player in PLAYERS:
            places += [entry.item_id for entry in self.broker.inventory_of(player).entries()]
        for destination_id in self.world.destination_ids():
            places += [item.item_id for item in self.world.destination(destination_id).contents()]
        return places

    def type(self, player, line):
        self.replies.append(self.front.submit(self.tokens[player], line))

    def check_the_game_is_consistent(self):
        items = self.all_items()
        self.assertEqual(len(items), len(set(items)), "an item is in two places at once")
        self.assertEqual(sorted(self.items_at_start), sorted(items),
                         "an item appeared or disappeared")
        for destination_id, resources in self.start_stock.items():
            for resource, amount in resources.items():
                in_bags = sum(self.broker.resources_of(p).amount_of(resource) for p in PLAYERS)
                left = self.deposits.available(destination_id, resource)
                with self.subTest(resource=resource):
                    self.assertEqual(amount, in_bags + left, f"{resource} was lost or made up")
        self.assertEqual(0, self.broker.pending_count(), "an operation is still in flight")
        self.assertEqual([], self.broker.picks_in_flight())
        for player in PLAYERS:
            states = {entry.state() for entry in self.broker.inventory_of(player).entries()}
            self.assertLessEqual(states, {"owned", "done"}, f"{player} has an item stuck in flight")
        for reply in self.replies:
            self.assertIsInstance(reply, str)
            self.assertTrue(reply, "a command got no answer")
            self.assertNotIn("something went wrong", reply)

    def test_players_one_after_another(self):
        for seed in (1, 2, 3):
            with self.subTest(seed=seed):
                dice = random.Random(seed)
                for _ in range(300):
                    self.type(dice.choice(PLAYERS), random_command(dice))
                self.check_the_game_is_consistent()

    def test_players_all_at_once(self):
        def play(player, seed):
            dice = random.Random(seed)
            for _ in range(80):
                self.type(player, random_command(dice))
        threads = [threading.Thread(target=play, args=(player, seed))
                   for seed, player in enumerate(PLAYERS, start=10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
            self.assertFalse(thread.is_alive(), "a player is still waiting for an answer")
        self.assertEqual(80 * len(PLAYERS), len(self.replies))
        self.check_the_game_is_consistent()


if __name__ == "__main__":
    unittest.main()