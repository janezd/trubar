import os
import shutil
import tempfile
import unittest

from trubar.messages import dict_to_msg_nodes, dict_from_msg_nodes


def yamlized(func):
    def yamlized_func(*args, **kwargs):
        args = [dict_to_msg_nodes(arg) if isinstance(arg, dict) else arg
                for arg in args]
        res = func(*args, **kwargs)
        return dict_from_msg_nodes(res) if isinstance(res, dict) else res
    return yamlized_func


class TestBase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmpdir = None

    def tearDown(self) -> None:
        super().tearDown()
        if self.tmpdir is not None:
            shutil.rmtree(self.tmpdir)

    def prepare_file(self, filename, s):
        if self.tmpdir is None:
            self.tmpdir = tempfile.mkdtemp()

        fn = os.path.join(self.tmpdir, filename)
        with open(fn, "w", encoding="utf-8") as f:
            f.write(s)
        return fn
