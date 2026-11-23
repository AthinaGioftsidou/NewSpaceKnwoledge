"""Unit tests for app/game.py: the whole game in one program."""

import tempfile
import unittest
from pathlib import Path

from spaceknowledge.app.game import build_game
from spaceknowledge.app.layout import WORLD_FILE
from spaceknowledge.tests.app.helpers import PASSWORD


class TestGame(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()      # a fresh "state" folder, never the real one
        self.addCleanup(folder.cleanup)
        self.state = Path(folder.name)

    def start(self):
        game = build_game(WORLD_FILE, self.state, iterations=1)
        self.addCleanup(game.close)                  # always stop both threads
        return game

    def test_the_whole_game_runs_in_one_program(self):
        front = self.start().front
        front.register("ada", PASSWORD)
        token = front.login("ada", PASSWORD)
        self.assertEqual("You are at Earth.", front.command(token, "where"))
        self.assertEqual("You mine 20 iron.", front.command(token, "mine iron 20"))
        self.assertTrue(front.command(token, "answer rust").startswith("Correct!"))
        self.assertTrue(front.command(token, "fly to mars").startswith("You fly to Mars."))

    def test_it_saves_everything_in_the_state_folder(self):
        front = self.start().front
        front.register("ada", PASSWORD)
        front.login("ada", PASSWORD)                 # joining the world saves both servers
        for name in ("universe.json", "players.json", "accounts.json", "server.key"):
            with self.subTest(file=name):
                self.assertTrue((self.state / name).exists())

    def test_a_restart_carries_on_where_it_stopped(self):
        first = self.start()
        first.front.register("ada", PASSWORD)
        token = first.front.login("ada", PASSWORD)
        first.front.command(token, "fly to the moon")
        first.close()
        again = self.start().front                   # same folder, fresh program
        token = again.login("ada", PASSWORD)          # the account is still there
        self.assertEqual("You are at The Moon.", again.command(token, "where"))

    def test_closing_twice_is_harmless(self):
        game = self.start()
        game.close()
        game.close()


if __name__ == "__main__":
    unittest.main()