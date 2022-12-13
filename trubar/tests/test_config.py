import dataclasses
import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from trubar.config import Configuration
from trubar.tests import TestBase, ExitCalled


class ConfigTest(TestBase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.tmpdir = tempfile.mkdtemp()
        cls.fn = os.path.join(cls.tmpdir, "test.yaml")
        cls.patch_exit()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir)
        super().tearDownClass()

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

    def test_exclude(self):
        config = Configuration()
        self.assertTrue(config.exclude_re.search("dir/tests/test_something.py"))
        self.prepare("exclude-pattern: ba?_m")
        config.update_from_file(self.fn)
        self.assertFalse(config.exclude_re.search("dir/tests/test_something.py"))
        self.prepare("exclude-pattern: ")
        config.update_from_file(self.fn)
        self.assertIsNone(config.exclude_re)

        config.set_exclude_pattern("tests/test_")
        self.assertTrue(config.exclude_re.search("dir/tests/test_something.py"))
        config.set_exclude_pattern("")
        self.assertIsNone(config.exclude_re)


if __name__ == "__main__":
    unittest.main()
