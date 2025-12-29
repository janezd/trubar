import os
import tempfile
from pathlib import PureWindowsPath

import unittest

from unittest.mock import patch, Mock

from trubar.utils import \
    walk_files, check_any_files, unique_name, dump_removed, make_list, \
    KeyMapping, _compressed, _decompressed, save_mapping, load_mapping

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
            check_any_files(set(translations), "foo/bar")
            exit_.assert_not_called()
            print_.assert_not_called()

        with patch("trubar.utils.walk_files",
                   Mock(return_value=[("t/x/" + k, k) for k in keys])):
            check_any_files(set(translations), "foo/bar")
            exit_.assert_called()
            print_.assert_called()
            msg = print_.call_args[0][0]
            self.assertIn("-s foo/bar/t/x", msg)
            print_.reset_mock()
            exit_.reset_mock()

            home = os.path.expanduser("~/foo/bar")
            check_any_files(set(translations), home)
            exit_.assert_called()
            msg = print_.call_args[0][0]
            self.assertIn("-s ~/foo/bar/t/x", msg)
            print_.reset_mock()
            exit_.reset_mock()

            with patch("sys.platform", "win32"):
                check_any_files(set(translations), home)
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
            check_any_files({"x.py", "z.py", "u.py"}, "foo")
            exit_.assert_called()
            print_.assert_called()
            msg = print_.call_args[0][0]
            self.assertIn("-s foo/a/b", msg)
            print_.reset_mock()
            exit_.reset_mock()

        keys = "a/x.py a/y.py a/b/x.py a/b/z.py".split()
        with patch("trubar.utils.walk_files",
                   Mock(return_value=[(k, k) for k in keys])):
            check_any_files({"x.py", "z.py", "u.py"}, "foo")
            exit_.assert_called()
            print_.assert_called()
            msg = print_.call_args[0][0]
            self.assertNotIn("-s foo/a/b", msg)
            print_.reset_mock()
            exit_.reset_mock()

    def test_unique_name(self):
        with patch("os.path.exists", return_value=False):
            self.assertEqual(unique_name("some name.yaml"),
                             "some name.yaml")

        with patch("os.path.exists", return_value=True):
            with patch("os.listdir", return_value=["some name.yaml"]) as listdir:
                self.assertEqual(unique_name("some name.yaml"),
                                 "some name (1).yaml")
                listdir.assert_called_with(".")

                self.assertEqual(unique_name("abc/def/some name.yaml"),
                                 "abc/def/some name (1).yaml")
                listdir.assert_called_with("abc/def")

            with patch("os.listdir", return_value=["some name.yaml",
                                                   "some name (1).yaml",
                                                   "some name (2).yaml",
                                                   "non sequitur.yaml",
                                                   ]) as listdir:
                self.assertEqual(unique_name("some name.yaml"),
                                 "some name (3).yaml")
                listdir.assert_called_with(".")

            with patch("os.listdir", return_value=["some name.yaml",
                                                   "some name (1).yaml",
                                                   "non sequitur.yaml",
                                                   "some name (4).yaml",
                                                   ]) as listdir:
                self.assertEqual(unique_name("some name.yaml"),
                                 "some name (5).yaml")
                listdir.assert_called_with(".")

    @patch("trubar.utils.dump")
    def test_dump_removed(self, mock_dump):
        dump_removed({}, "removed.yaml", "abc/def/x.yaml")
        mock_dump.assert_not_called()

        msgs = Mock()
        dump_removed(msgs, "removed.yaml", "abc/def/x.yaml")
        mock_dump.assert_called_with(msgs, "removed.yaml")

        dump_removed(msgs, None, "abc/def/xyz.jaml")
        mock_dump.assert_called_with(msgs, "abc/def/removed-from-xyz.jaml")

    def test_make_list(self):
        self.assertEqual(make_list(["a"]), "a")
        self.assertEqual(make_list(["a", "b"]), "a and b")
        self.assertEqual(make_list(["a", "b", "c"]), "a, b and c")
        self.assertEqual(make_list(["a"], "use"), "a uses")
        self.assertEqual(make_list(["a", "b", "c"], "use"), "a, b and c use")

class TestMappingCompression(unittest.TestCase):
    key_mapping = [
        KeyMapping(path=('some', 'path'), f_lang_idx=(0, 1), raw=True),
        KeyMapping(path=('some', 'other', 'path', 'somewhere'), f_lang_idx=(0, 1), raw=True),
        KeyMapping(path=('some', 'other', 'path', 'elsewhere')),
        KeyMapping(path=('some', 'third', 'path'), raw=True),
        KeyMapping(path=('some', 'completely', 'different'), raw=False),
        KeyMapping(path=('some', 'completely', 'beyond', 'different'), raw=False),
        KeyMapping(path=('really', 'different'), f_lang_idx=(0, 1), raw=True),
        KeyMapping(path=('really', 'really', 'different'), f_lang_idx=(0, 1), raw=True),
        KeyMapping(path=('not-same',), f_lang_idx=(0, 1), raw=True)
    ]

    def test_compression(self):
        compressed = _compressed(self.key_mapping)
        self.assertEqual(
            compressed,
            [[0, ('some', 'path'), (0, 1), True],
             [1, ('other', 'path', 'somewhere'), (0, 1), True],
             [3, ('elsewhere',)],
             [1, ('third', 'path'), (), True],
             [1, ('completely', 'different')],
             [2, ('beyond', 'different')],
             [0, ('really', 'different'), (0, 1), True],
             [1, ('really', 'different'), (0, 1), True],
             [0, ('not-same',), (0, 1), True]]
        )

        self.assertEqual(_decompressed(compressed), self.key_mapping)

    def test_loading_saving(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            languages = ["en", "fr", "de"]
            save_mapping(tmpdirname, languages, self.key_mapping)
            loaded_languages, loaded_mapping = load_mapping(tmpdirname)

            self.assertEqual(loaded_languages, languages)
            self.assertEqual(loaded_mapping, self.key_mapping)

if __name__ == "__main__":
    unittest.main()
