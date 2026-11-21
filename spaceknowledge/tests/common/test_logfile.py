"""Unit tests for common/logfile.py."""

import logging
import tempfile
import unittest
from datetime import date
from pathlib import Path

from spaceknowledge.common.logfile import close_log, log_path, open_log


class TestLogFile(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.day = date(2026, 1, 15)  # a fixed day, so we know the file name

    def test_file_is_named_after_the_day(self):
        self.assertEqual(self.folder / "2026-01-15_spaceknowledge.log",
                         log_path(self.folder, self.day))

    def test_message_from_a_module_reaches_the_file(self):
        handler = open_log(self.folder, self.day)
        try:
            logging.getLogger("spaceknowledge.broker.broker_server").info("ada mined 5 iron")
        finally:
            close_log(handler)
        text = log_path(self.folder, self.day).read_text(encoding="utf-8")
        self.assertIn("ada mined 5 iron", text)


if __name__ == "__main__":
    unittest.main()