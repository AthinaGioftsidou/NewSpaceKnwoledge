"""Unit tests for app/settings.py."""

import json
import tempfile
import unittest
from pathlib import Path

from spaceknowledge.app.settings import Settings, SettingsError, is_valid_name, load_settings


class TestSettings(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "settings.json"

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def test_no_file_means_the_defaults(self):
        settings = load_settings(self.path)
        self.assertEqual(("127.0.0.1", 7400), (settings.universe_host, settings.universe_port))
        self.assertEqual(("broker-1", "broker-2"), settings.brokers)
        self.assertEqual(("earth", ("root",)), (settings.start, settings.admins))

    def test_each_broker_gets_the_next_dmz_port(self):
        settings = Settings()
        self.assertEqual(8400, settings.dmz_port("broker-1"))
        self.assertEqual(8401, settings.dmz_port("broker-2"))
        with self.assertRaises(SettingsError):
            settings.dmz_port("broker-9")

    def test_a_file_changes_only_what_it_names(self):
        self.write(json.dumps({"brokers": ["alpha", "beta", "gamma"], "universe_port": 7500}))
        settings = load_settings(self.path)
        self.assertEqual(("alpha", "beta", "gamma"), settings.brokers)   # a list became a tuple
        self.assertEqual(7500, settings.universe_port)
        self.assertEqual("earth", settings.start)                         # untouched: default

    def test_a_file_that_cannot_be_trusted_is_refused(self):
        for text in ("{ not json", "[1, 2]", '{"brokers": "broker-1"}', '{"colour": "blue"}'):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaises(SettingsError):
                    load_settings(self.path)

    def test_values_that_make_no_sense_are_refused(self):
        bad = [
            {"brokers": ("broker-1", "broker-1")},           # listed twice
            {"brokers": ("Broker One",)},                    # not a valid name
            {"universe_port": 70000},                        # no such port
            {"universe_port": 8401},                         # clashes with broker-2's DMZ
            {"admins": ("Root",)},                           # must already be lower case
            {"admins": ()},                                  # nobody
        ]
        for values in bad:
            with self.subTest(values=values):
                with self.assertRaises(SettingsError):
                    Settings(**values)

    def test_what_makes_a_valid_broker_name(self):
        self.assertTrue(is_valid_name("broker-1"))
        for name in ("universe", "../evil", "Broker", "", "-start", "x" * 31, 7):
            with self.subTest(name=name):
                self.assertFalse(is_valid_name(name))


if __name__ == "__main__":
    unittest.main()