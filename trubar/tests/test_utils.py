import os
from pathlib import PureWindowsPath

import unittest

from unittest.mock import patch, Mock

from trubar.utils import walk_files, check_any_files
from trubar.config import config
import trubar.tests.test_module


test_module_path = os.path.split(trubar.tests.test_module.__file__)[0]


class UtilsTest(unittest.TestCase):
    def test_walk_files(self):
        tmp = test_module_path
        old_pattern = config.exclude_pattern
        try:
            config.set_exclude_pattern("")
            self.assertEqual(
                set(walk_files(tmp, select=True)),
                {('bar_module/__init__.py',
                  f'{tmp}/bar_module/__init__.py'),
                 ('bar_module/foo_module/__init__.py',
                  f'{tmp}/bar_module/foo_module/__init__.py'),
                 ('baz_module/__init__.py',
                  f'{tmp}/baz_module/__init__.py'),
                 ('__init__.py',
                  f'{tmp}/__init__.py')}
            )

            old_path = os.getcwd()
            try:
                os.chdir(tmp)
                self.assertEqual(
                    set(walk_files(".", select=True)),
                    {('bar_module/__init__.py',
                      './bar_module/__init__.py'),
                     ('bar_module/foo_module/__init__.py',
                      './bar_module/foo_module/__init__.py'),
                     ('baz_module/__init__.py',
                      './baz_module/__init__.py'),
                     ('__init__.py',
                      './__init__.py')}
                )
                self.assertEqual(
                    set(walk_files(".", "bar", select=True)),
                    {('bar_module/__init__.py',
                      './bar_module/__init__.py'),
                     ('bar_module/foo_module/__init__.py',
                      './bar_module/foo_module/__init__.py')}
                )
            finally:
                os.chdir(old_path)

            self.assertEqual(
                set(walk_files(tmp, select=False)),
                {('bar_module/__init__.py',
                  f'{tmp}/bar_module/__init__.py'),
                 ('bar_module/foo_module/__init__.py',
                  f'{tmp}/bar_module/foo_module/__init__.py'),
                 ('baz_module/__init__.py',
                  f'{tmp}/baz_module/__init__.py'),
                 ('__init__.py',
                  f'{tmp}/__init__.py'),
                 ('baz_module/not-python.js',
                  f'{tmp}/baz_module/not-python.js')}
            )

            config.set_exclude_pattern("b?r_")
            self.assertEqual(
                set(walk_files(tmp, select=False)),
                {('bar_module/__init__.py',
                  f'{tmp}/bar_module/__init__.py'),
                 ('bar_module/foo_module/__init__.py',
                  f'{tmp}/bar_module/foo_module/__init__.py'),
                 ('baz_module/__init__.py',
                  f'{tmp}/baz_module/__init__.py'),
                 ('__init__.py',
                  f'{tmp}/__init__.py'),
                 ('baz_module/not-python.js',
                  f'{tmp}/baz_module/not-python.js')}
            )
            self.assertEqual(
                set(walk_files(tmp, select=True)),
                {('baz_module/__init__.py',
                  f'{tmp}/baz_module/__init__.py'),
                 ('__init__.py',
                  f'{tmp}/__init__.py')}
            )
        finally:
            config.set_exclude_pattern(old_pattern)

    @patch("os.walk",
           return_value=[(r"c:\foo\bar\ann\bert",
                          None,
                          ["cecil.py", "dan.txt", "emily.py"])]
           )
    @patch("os.path.join", new=lambda *c: "\\".join(c))
    @patch("trubar.utils.PurePath", new=PureWindowsPath)
    def test_walk_backslashes_on_windows(self, _):
        self.assertEqual(
            list(walk_files(r"c:\foo\bar", select=False)),
            [("ann/bert/cecil.py", r"c:\foo\bar\ann\bert\cecil.py"),
             ("ann/bert/dan.txt", r"c:\foo\bar\ann\bert\dan.txt"),
             ("ann/bert/emily.py", r"c:\foo\bar\ann\bert\emily.py")]
        )
        self.assertEqual(
            list(walk_files(r"c:\foo\bar", "l", select=False)),
            [("ann/bert/cecil.py", r"c:\foo\bar\ann\bert\cecil.py"),
             ("ann/bert/emily.py", r"c:\foo\bar\ann\bert\emily.py")])
        # Don't match pattern in path
        self.assertEqual(
            list(walk_files(r"c:\foo\bar", "o", select=False)),
            [])

    @patch("sys.exit")
    @patch("builtins.print")
    def test_check_any_files(self, print_, exit_):
        keys = "a/x.py a/y.py a/b/x.py a/b/z.py".split()
        translations = dict.fromkeys(keys)
        with patch("trubar.utils.walk_files",
                   Mock(return_value=[(k, k) for k in keys])):
            check_any_files(translations, "foo/bar")
            exit_.assert_not_called()
            print_.assert_not_called()

        with patch("trubar.utils.walk_files",
                   Mock(return_value=[("t/x/" + k, k) for k in keys])):
            check_any_files(translations, "foo/bar")
            exit_.assert_called()
            print_.assert_called()
            msg = print_.call_args[0][0]
            self.assertIn("-s foo/bar/t/x", msg)
            print_.reset_mock()
            exit_.reset_mock()

            home = os.path.expanduser("~/foo/bar")
            check_any_files(translations, home)
            exit_.assert_called()
            msg = print_.call_args[0][0]
            self.assertIn("-s ~/foo/bar/t/x", msg)
            print_.reset_mock()
            exit_.reset_mock()

            with patch("sys.platform", "win32"):
                check_any_files(translations, home)
                exit_.assert_called()
                print_.assert_called()
                msg = print_.call_args[0][0]
                print_.assert_called()
                self.assertIn(f"-s {home}/t/x", msg)
                print_.reset_mock()
                exit_.reset_mock()

        keys = "a/x.py a/y.py a/b/x.py a/b/z.py a/b/u.py".split()
        with patch("trubar.utils.walk_files",
                   Mock(return_value=[(k, k) for k in keys])):
            check_any_files(dict.fromkeys(["x.py", "z.py", "u.py"]), "foo")
            exit_.assert_called()
            print_.assert_called()
            msg = print_.call_args[0][0]
            self.assertIn("-s foo/a/b", msg)
            print_.reset_mock()
            exit_.reset_mock()

        keys = "a/x.py a/y.py a/b/x.py a/b/z.py".split()
        with patch("trubar.utils.walk_files",
                   Mock(return_value=[(k, k) for k in keys])):
            check_any_files(dict.fromkeys(["x.py", "z.py", "u.py"]), "foo")
            exit_.assert_called()
            print_.assert_called()
            msg = print_.call_args[0][0]
            self.assertNotIn("-s foo/a/b", msg)
            print_.reset_mock()
            exit_.reset_mock()


if __name__ == "__main__":
    unittest.main()
