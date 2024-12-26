import os

import dataclasses
import unittest
from unittest.mock import patch

from trubar.config import Configuration, LanguageDef
from trubar.tests import TestBase


class ConfigTest(TestBase):
    def prepare(self, s):
        # pylint: disable=attribute-defined-outside-init
        self.fn = self.prepare_file("test.yaml", s)

    def test_proper_file(self):
        config = Configuration()
        self.prepare("smart_quotes: false\n\nencoding: cp-1234")
        config.update_from_file(self.fn)
        self.assertFalse(config.smart_quotes)
        self.assertTrue(config.auto_prefix)
        self.assertEqual(config.encoding, "cp-1234")

    @patch("builtins.print")
    def test_malformed_file(self, _):
        config = Configuration()
        self.prepare("smart_quotes: false\n\nencoding")
        self.assertRaises(SystemExit, config.update_from_file, self.fn)

    @patch("builtins.print")
    def test_unrecognized_option(self, a_print):
        config = Configuration()
        self.prepare("smart_quotes: false\n\nauto_magog: false")
        self.assertRaises(SystemExit, config.update_from_file, self.fn)
        self.assertIn("auto_magog", a_print.call_args[0][0])

    @patch("builtins.print")
    def test_invalid_type(self, a_print):
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
        self.assertRaises(SystemExit, config.update_from_file, self.fn)
        self.assertIn("foo", a_print.call_args[0][0])

    @patch("builtins.print")
    def test_static_files(self, _):
        config = Configuration()
        self.assertEqual(len(config.static_files), 0)

        self.prepare("static-files: static_files_lan")
        with patch("os.path.exists", lambda x: "test.yaml" in x):
            self.assertRaises(SystemExit, config.update_from_file, self.fn)

        with patch("os.path.exists", lambda _: True):
            config = Configuration()
            config.update_from_file(self.fn)
            self.assertEqual(config.static_files, ("static_files_lan", ))

        self.prepare("static-files:\n"
                     "- static_files_lan\n"
                     "- ban\n"
                     "- pet_podgan\n")
        with patch("os.path.exists", lambda x: "test.yaml" in x or "lan" in x):
            self.assertRaises(SystemExit, config.update_from_file, self.fn)

        with patch("os.path.exists", lambda x: "test.yaml" in x or "an" in x):
            config = Configuration()
            config.update_from_file(self.fn)
            self.assertEqual(config.static_files,
                             ("static_files_lan", "ban", "pet_podgan"))

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

    def test_languages(self):
        self.prepare("""
            languages:
                si:
                    name: Slovenščina
                    international-name: Slovenian
                    auto-import: from orangecanvas.localization.si import plsi
                en:
                    name: English
                    original: true
                ua:
                    international-name: Ukrainian
                    auto-import: import grain
                    name: Українська
            auto-import: from orangecanvas.localization import pl
""")
        config = Configuration()
        with patch("os.path.exists",
                   lambda path: not os.path.join("si", "static") in path):
            config.update_from_file(self.fn)
            # Language definitions are correct
            self.assertEqual(
                config.languages,
                {'en': LanguageDef(name='English',
                                   international_name='English',
                                   is_original=True),
                 'si': LanguageDef(name='Slovenščina',
                                   international_name='Slovenian',
                                   is_original=False),
                 'ua': LanguageDef(name='Українська',
                                   international_name='Ukrainian',
                                   is_original=False)})
            # Original language is first
            self.assertTrue(next(iter(config.languages.values())).is_original)
            # Auto-imports are correct
            self.assertEqual(
                set(config.auto_import),
                {'from orangecanvas.localization.si import plsi',
                 'import grain',
                 'from orangecanvas.localization import pl'})
            # Base dir is set correctly
            base_dir, _ = os.path.split(self.fn)
            self.assertEqual(config.base_dir, base_dir)
            # Static files are correct
            self.assertEqual(
                set(config.static_files),
                {os.path.join(base_dir, "en", "static"),
                 os.path.join(base_dir, "ua", "static")}
            )

    @patch("builtins.print")
    def test_languages_unknown_option(self, a_print):
        self.prepare("""
            languages:
                si:
                    name: Slovenščina
                    encoding: utf-8
                    foo: bar
                en:
                    name: English
                    original: true
        """)
        with patch("os.path.exists", lambda _: True):
            config = Configuration()
            self.assertRaises(SystemExit, config.update_from_file, self.fn)
            self.assertEqual(
                a_print.call_args[0][0],
                "Unknown options for language 'si': encoding, foo")

    @patch("builtins.print")
    def test_languages_missing_name(self, a_print):
        self.prepare("""
                languages:
                    si:
                        name: Slovenščina
                    en:
                        original: true
        """)
        with patch("os.path.exists", lambda _: True):
            config = Configuration()
            self.assertRaises(SystemExit, config.update_from_file, self.fn)
            self.assertEqual(
                a_print.call_args[0][0],
                "Language 'en' is missing a 'name' option")

    @patch("builtins.print")
    def test_languages_missing_directory(self, a_print):
        self.prepare("""
                languages:
                    si:
                        name: Slovenščina
                    foo-bar-langa:
                        name: fubar
                    en:
                        original: true
        """)
        with patch("os.path.exists", lambda path: "foo-bar-lang" not in path):
            config = Configuration()
            self.assertRaises(SystemExit, config.update_from_file, self.fn)
            self.assertIn(
                "Directory for language 'foo-bar-langa' is missing",
                a_print.call_args[0][0])

    @patch("builtins.print")
    def test_no_original_language(self, a_print):
        self.prepare("""
                languages:
                    si:
                        name: Slovenščina
                    en:
                        name: English
        """)
        with patch("os.path.exists", lambda _: True):
            config = Configuration()
            self.assertRaises(SystemExit, config.update_from_file, self.fn)
            self.assertEqual(
                "Original language is not defined",
                a_print.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
