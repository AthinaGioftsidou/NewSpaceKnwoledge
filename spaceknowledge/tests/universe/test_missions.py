"""Unit tests for universe/missions.py, using the mission in data/space.json."""

import json
import unittest
from pathlib import Path

from spaceknowledge.universe.missions import (
    COLLECTING, COMPLETE, QUESTION, MissionBook, MissionError,
)

SPACE_FILE = Path(__file__).resolve().parents[3] / "data" / "space.json"


class TestMissions(unittest.TestCase):

    def setUp(self):
        self.raw = json.loads(SPACE_FILE.read_text(encoding="utf-8"))
        self.book = MissionBook.from_raw(self.raw)
        self.mission = self.book.current()       # "ship_upgrade": mine 20 iron on Earth

    def test_the_mission_is_read_from_the_world_file(self):
        self.assertEqual("ship_upgrade", self.mission.mission_id)
        self.assertEqual("mission:ship_upgrade", self.mission.key())
        self.assertEqual(COLLECTING, self.book.status("ship_upgrade"))

    def test_only_the_right_resource_in_the_right_place_counts(self):
        self.book.record_mining("moon", "iron", 5)        # wrong place
        self.book.record_mining("earth", "wood", 5)       # wrong resource
        self.book.record_mining("earth", "iron", 5)       # counts
        self.assertEqual(5, self.book.collected("ship_upgrade"))

    def test_enough_mining_asks_the_question(self):
        self.book.record_mining("earth", "iron", 15)
        self.book.record_mining("earth", "iron", 15)      # more than needed
        self.assertEqual(20, self.book.collected("ship_upgrade"))   # capped at the goal
        self.assertEqual(QUESTION, self.book.status("ship_upgrade"))

    def test_no_answer_is_taken_before_the_question(self):
        self.assertIsNone(self.book.answer("iron"))

    def test_a_wrong_answer_then_a_right_one(self):
        self.book.record_mining("earth", "iron", 20)
        self.assertEqual((self.mission, False), self.book.answer("copper"))
        self.assertEqual((self.mission, True), self.book.answer("I think it is Iron Oxide!"))
        self.assertEqual(COMPLETE, self.book.status("ship_upgrade"))

    def test_answers_must_be_whole_words_and_short(self):
        self.assertFalse(self.mission.accepts("ironic"))            # "iron" is not a whole word
        self.assertFalse(self.mission.accepts("one two three four five six seven iron"
                                              " nine"))              # 9 words: too long

    def test_bad_saved_progress_is_refused_and_changes_nothing(self):
        with self.assertRaises(MissionError):
            self.book.restore({"ship_upgrade": {"collected": 999, "complete": False}})
        self.assertEqual(0, self.book.collected("ship_upgrade"))

    def test_an_unexpected_field_in_the_file_is_refused(self):
        self.raw["missions"][0]["reward"] = "gold"
        with self.assertRaises(MissionError):
            MissionBook.from_raw(self.raw)


if __name__ == "__main__":
    unittest.main()