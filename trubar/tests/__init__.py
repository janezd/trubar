import sys
import unittest
from unittest.mock import Mock
from contextlib import contextmanager


class ExitCalled(Exception):
    pass


@contextmanager
def patched_exit():
    old_exit = sys.exit
    sys.exit = Mock(side_effect=ExitCalled)
    try:
        yield
    finally:
        sys.exit = old_exit


class TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old_exit = None

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.old_exit is not None:
            sys.exit = cls.old_exit

    @classmethod
    def patch_exit(cls):
        cls.old_exit = sys.exit
        sys.exit = Mock(side_effect=ExitCalled)
