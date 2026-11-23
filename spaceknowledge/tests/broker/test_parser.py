"""Unit tests for broker/parser.py."""

import unittest

from spaceknowledge.broker.command import (
    AnswerCommand, FlyCommand, InventoryCommand, LookCommand, MineCommand, PickCommand,
)
from spaceknowledge.broker.parser import ParseError, Parser


class TestParser(unittest.TestCase):

    def setUp(self):
        self.parser = Parser()

    def test_words_with_nothing_after_them(self):
        self.assertIsInstance(self.parser.parse("inventory"), InventoryCommand)
        self.assertIsInstance(self.parser.parse("  I  "), InventoryCommand)   # short form, any case
        self.assertIsInstance(self.parser.parse("look"), LookCommand)
        with self.assertRaisesRegex(ParseError, "does not take anything after it"):
            self.parser.parse("look around")

    def test_filler_words_and_articles_are_skipped(self):
        pick = self.parser.parse("pick up the torch")
        self.assertIsInstance(pick, PickCommand)
        self.assertEqual("torch", pick.target)
        self.assertEqual("torch", self.parser.parse("take a torch").target)
        fly = self.parser.parse("Fly to Mars")
        self.assertIsInstance(fly, FlyCommand)
        self.assertEqual("mars", fly.target)

    def test_a_name_can_be_several_words(self):
        answer = self.parser.parse("answer iron oxide")
        self.assertIsInstance(answer, AnswerCommand)
        self.assertEqual("iron oxide", answer.target)

    def test_mine_takes_an_optional_amount(self):
        three = self.parser.parse("mine iron 3")
        self.assertIsInstance(three, MineCommand)
        self.assertEqual(("iron", 3), (three.resource, three.amount))
        self.assertEqual(("iron", 1), (self.parser.parse("mine iron").resource,
                                       self.parser.parse("mine iron").amount))
        self.assertEqual("helium_3", self.parser.parse("mine helium_3").resource)
        with self.assertRaisesRegex(ParseError, "at least 1"):
            self.parser.parse("mine iron 0")

    def test_a_missing_name_says_what_is_missing(self):
        with self.assertRaisesRegex(ParseError, "which destination"):
            self.parser.parse("fly to")
        with self.assertRaisesRegex(ParseError, "which item"):
            self.parser.parse("drop")
        with self.assertRaisesRegex(ParseError, "which resource"):
            self.parser.parse("mine 5")

    def test_unknown_or_empty_lines_are_refused(self):
        with self.assertRaisesRegex(ParseError, "no verb called 'dance'"):
            self.parser.parse("dance")
        with self.assertRaises(ParseError):
            self.parser.parse("   ")

    def test_verbs_lists_every_word_once(self):
        verbs = self.parser.verbs()
        self.assertEqual(sorted(verbs), verbs)
        for word in ("fly", "go", "i", "mine", "take", "answer"):
            self.assertIn(word, verbs)


if __name__ == "__main__":
    unittest.main()