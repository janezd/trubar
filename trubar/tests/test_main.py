import os
import unittest
from unittest.mock import patch

from trubar.__main__ import check_dir_exists

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


if __name__ == "__main__":
    unittest.main()
