import dataclasses
import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from trubar.config import Configuration


class ExitCalled(Exception):
    pass


class ConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.mkdtemp()
        cls.fn = os.path.join(cls.tmpdir, "test.yaml")
        cls.old_exit = sys.exit
        sys.exit = Mock(side_effect=ExitCalled)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir)
        sys.exit = cls.old_exit

    def prepare(self, s):
        with open(self.fn, "w") as f:
            f.write(s)

    def test_proper_file(self):
        config = Configuration()
        self.prepare("auto_quotes: false\n\nencoding: cp-1234")
        config.update_from_file(self.fn)
        self.assertFalse(config.auto_quotes)
        self.assertTrue(config.auto_prefix)
        self.assertEqual(config.encoding, "cp-1234")

    def test_malformed_file(self):
        config = Configuration()
        self.prepare("auto_quotes: false\n\nencoding")
        self.assertRaises(ExitCalled, config.update_from_file, self.fn)

    def test_unrecognized_option(self):
        config = Configuration()
        self.prepare("auto_quotes: false\n\nauto_magog: false")
        self.assertRaises(ExitCalled, config.update_from_file, self.fn)

    def test_invalid_type(self):
        # At the time of writing, Configuration had only bool and str settings,
        # which can never fail on conversion. To reach that code in test, we
        # imagine setting that can
        # Data classes do not support inheritance, so we patch the tested method
        # into a new class.
        @dataclasses.dataclass
        class ConfigurationWithInt:
            encoding: str = "ascii"
            foo: int = 42
            update_from_file = Configuration.update_from_file

        config = ConfigurationWithInt()
        self.prepare("foo: bar")
        self.assertRaises(ExitCalled, config.update_from_file, self.fn)

    @patch("builtins.print")
    def test_static_files(self, _):
        config = Configuration()
        self.assertEqual(config.static_files, "")

        self.prepare("static-files: static_files_lan")
        with patch("os.path.exists", Mock(return_value=False)):
            self.assertRaises(ExitCalled, config.update_from_file, self.fn)

        with patch("os.path.exists", Mock(return_value=True)):
            config.update_from_file(self.fn)
            self.assertEqual(config.static_files, "static_files_lan")


if __name__ == "__main__":
    unittest.main()
