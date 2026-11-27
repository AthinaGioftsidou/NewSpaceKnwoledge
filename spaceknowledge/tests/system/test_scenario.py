"""SCENARIO TEST: one player's whole journey, typed one command at a time.

Ada logs in on Earth, drops and picks up her torch, mines iron for the
mission, answers its question, flies to Mars to mine nickel, comes back, flies
to the Moon and mines helium-3. After every command the test checks the
answer, so a failure says exactly which step went wrong.

It plays through the real front door: the broker web server over HTTP, with
the real GameClient, the same class the terminal program uses.
"""

import unittest

from spaceknowledge.client.game_client import GameClient
from spaceknowledge.tests.app.helpers import PASSWORD
from spaceknowledge.tests.broker_web.web_helpers import a_broker_web

# (what ada types, how the answer must begin)
SCENARIO = [
    ("Look",              "Nothing lies on the ground here."),
    ("Where",             "You are at Earth."),
    ("Inventory",         "You are carrying: torch"),
    ("drop torch",        "You drop the torch."),
    ("pick torch",        "You pick up the torch."),
    ("mission",           "Mission: Upgrade the ship (collecting)\nCollected 0 of 20 iron."),
    ("mine iron 5",       "You mine 5 iron."),
    ("mine iron 50",      "You mine 50 iron."),
    ("mission",           "Mission: Upgrade the ship (question)"),
    ("answer rust",       "Correct! You have completed Upgrade the ship."),
    ("fly mars",          "You fly to Mars."),
    ("mine nickel 50",    "You mine 50 nickel."),
    ("i",                 "You are carrying: torch\nResources: iron 55, nickel 50"),
    ("fly earth",         "You fly to Earth."),
    ("where",             "You are at Earth."),
    ("fly moon",          "You fly to The Moon."),
    ("where",             "You are at The Moon."),
    ("mine helium_3 68",  "You mine 68 helium_3."),
    ("inventory",         "You are carrying: torch\nResources: helium_3 68, iron 55, nickel 50"),
]


class TestScenario(unittest.TestCase):

    def setUp(self):
        web, _, _ = a_broker_web(self)
        self.client = GameClient(*web.address)
        self.assertIsNone(self.client.register("ada", PASSWORD))
        self.token = self.client.login("ada", PASSWORD)

    def test_ada_completes_the_mission_and_visits_every_planet(self):
        for step, (line, expected) in enumerate(SCENARIO, start=1):
            with self.subTest(step=step, typed=line):
                reply = self.client.command(self.token, line)
                self.assertTrue(reply.startswith(expected),
                                f"step {step}, '{line}': expected {expected!r}, got {reply!r}")

    def test_the_gate_to_mars_stays_shut_until_the_mission_is_done(self):
        # The same journey without the answer: flying to Mars must be refused.
        for line in ("mine iron 5", "mine iron 50"):
            self.client.command(self.token, line)
        refused = self.client.command(self.token, "fly mars")
        self.assertTrue(refused.startswith("Refused: fly mars."), refused)
        self.assertIn("shut", refused)


if __name__ == "__main__":
    unittest.main()