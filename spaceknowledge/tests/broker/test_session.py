"""Unit tests for broker/command.py and broker/session.py: typed text in, text out,
against a real Broker and Universe."""

import unittest

from spaceknowledge.broker.broker import Broker
from spaceknowledge.broker.parser import Parser
from spaceknowledge.broker.session import Session
from spaceknowledge.tests.universe.test_universe import a_universe
from spaceknowledge.transport.channel import InMemoryChannel


class TestSession(unittest.TestCase):

    def setUp(self):
        self.broker = Broker(InMemoryChannel(a_universe()))
        self.broker.join("ada", "earth")
        self.session = Session(self.broker, Parser(), "ada")

    def say(self, line):
        return self.session.submit(line)

    def test_help_lists_what_can_be_typed(self):
        reply = self.say("help")
        self.assertTrue(reply.startswith("You can: answer, drop, fly, get, go, i, inventory"))
        self.assertTrue(reply.endswith(", help"))

    def test_a_line_the_parser_cannot_read_becomes_a_refusal(self):
        self.assertEqual("Refused: dance. Why: there is no verb called 'dance'. "
                         "Next: type help to see what you can do.", self.say("dance"))

    def test_inventory_shows_items_and_resources(self):
        self.assertEqual("You are carrying: torch", self.say("inventory"))
        self.say("mine iron 5")
        self.assertEqual("You are carrying: torch\nResources: iron 5", self.say("i"))
        self.say("drop torch")
        self.assertEqual("Resources: iron 5", self.say("i"))

    def test_drop_look_and_pick(self):
        self.assertEqual("Nothing lies on the ground here.", self.say("look"))
        self.assertEqual("You drop the torch.", self.say("drop the torch"))
        self.assertEqual("On the ground here: torch", self.say("look"))
        self.assertEqual("You pick up the torch.", self.say("pick up the torch"))

    def test_where_and_fly(self):
        self.assertEqual("You are at Earth.", self.say("where"))
        self.assertTrue(self.say("fly to the moon").startswith("You fly to The Moon.\nEarth's only"))
        self.assertTrue(self.say("fly to mars").startswith("Refused:"))   # no route from the Moon

    def test_the_mission_from_start_to_finish(self):
        self.assertTrue(self.say("mission").startswith(
            "Mission: Upgrade the ship (collecting)\nCollected 0 of 20 iron."))
        self.say("mine iron 20")
        self.assertIn("think again", self.say("answer copper"))
        self.assertTrue(self.say("answer rust").startswith(
            "Correct! You have completed Upgrade the ship.\nMars is red"))

    def test_a_player_the_broker_does_not_know(self):
        stranger = Session(self.broker, Parser(), "bob")
        self.assertIn("does not know a player called bob", stranger.submit("inventory"))


if __name__ == "__main__":
    unittest.main()