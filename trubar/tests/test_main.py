import os
import unittest
from unittest.mock import patch

from trubar.config import config
from trubar.__main__ import check_dir_exists, load_config

import trubar.tests.test_module

test_module_path = os.path.split(trubar.tests.test_module.__file__)[0]


class TestUtils(unittest.TestCase):
    @patch("builtins.print")
    def test_check_dir_exists(self, print_):
        check_dir_exists(test_module_path)
        print_.assert_not_called()

        self.assertRaises(
            SystemExit, check_dir_exists,
            os.path.join(test_module_path, "__init__.py"))
        self.assertIn("not a directory", print_.call_args[0][0])

        self.assertRaises(SystemExit, check_dir_exists, "no_such_path")
        self.assertNotIn("not a directory", print_.call_args[0][0])

    @patch.object(config, "update_from_file")
    def test_load_config(self, update):
        class Args:
            source = os.path.join("x", "y", "z")
            conf = ""

        args = Args()

        args.conf = "foo.yaml"
        load_config(args)
        update.assert_called_with("foo.yaml")
        update.reset_mock()
        args.conf = ""

        with patch("os.path.exists",
                   lambda x: os.path.split(x)[-1] in ("trubar-config.yaml",
                                                      ".trubarconfig.yaml")):
            load_config(args)
        update.assert_called_with(".trubarconfig.yaml")

        with patch("os.path.exists",
                   lambda x: os.path.split(x)[-1] == "trubar-config.yaml"):
            load_config(args)
        update.assert_called_with("trubar-config.yaml")

        confile = os.path.join(args.source, ".trubarconfig.yaml")
        with patch("os.path.exists", lambda x: x == confile):
            load_config(args)
        update.assert_called_with(confile)


if __name__ == "__main__":
    unittest.main()
