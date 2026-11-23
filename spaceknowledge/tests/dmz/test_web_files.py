"""Unit tests for the three web files: they follow the page's safety rules,
and every planet in space.json has its own background."""

import json
import re
import unittest

from spaceknowledge.app.layout import WORLD_FILE
from spaceknowledge.dmz.web_assets import WEB_DIR


def slug(name):
    """The same rule as `slug` in app.js: "The Moon" becomes "moon"."""
    name = re.sub(r"^the\s+", "", name.lower().strip())
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


class TestWebFiles(unittest.TestCase):

    def read(self, name):
        return (WEB_DIR / name).read_text(encoding="utf-8")

    def test_the_page_has_no_script_or_style_written_inside_it(self):
        page = self.read("index.html")
        self.assertIn('<script src="/app.js"></script>', page)
        self.assertNotIn("<style", page)
        self.assertNotIn(" style=", page)
        self.assertNotIn("onclick", page)

    def test_the_script_never_turns_text_into_markup(self):
        script = self.read("app.js")
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)

    def test_every_planet_has_a_background(self):
        styles = self.read("style.css")
        world = json.loads(WORLD_FILE.read_text(encoding="utf-8"))
        for place in world["destinations"]:
            with self.subTest(place=place["name"]):
                self.assertIn(f".planet-{slug(place['name'])}", styles)


if __name__ == "__main__":
    unittest.main()