"""Unit tests for dmz/web_assets.py: the three pages the DMZ may serve."""

import tempfile
import unittest
from pathlib import Path

from spaceknowledge.dmz.web_assets import WEB_DIR, load_assets


class TestWebAssets(unittest.TestCase):

    def test_exactly_three_pages_are_served(self):
        assets = load_assets(WEB_DIR)
        self.assertEqual({"/", "/app.js", "/style.css"}, set(assets))
        self.assertEqual("text/html; charset=utf-8", assets["/"].content_type)
        self.assertIn(b"<title>Space Knowledge</title>", assets["/"].data)

    def test_nothing_else_on_disk_can_be_reached(self):
        assets = load_assets(WEB_DIR)
        for path in ("/index.html", "/../settings.json", "/web/app.js"):
            with self.subTest(path=path):
                self.assertNotIn(path, assets)

    def test_a_missing_page_stops_the_start(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        (Path(folder.name) / "index.html").write_text("<p>only one</p>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "app.js is missing"):
            load_assets(Path(folder.name))


if __name__ == "__main__":
    unittest.main()