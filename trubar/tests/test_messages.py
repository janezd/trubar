import io
from contextlib import redirect_stdout
import unittest
from unittest.mock import patch

from trubar import messages
from trubar.messages import \
    load, dump, dict_to_msg_nodes, dict_from_msg_nodes, MsgNode

from trubar.tests import TestBase, yamlized


class TestUtils(TestBase):
    def test_load_yaml(self):
        fn = self.prepare_file("x.yaml", """
    class `A`:
        foo: bar
        boo: null
        def `f`:
            def `g`:
                vaz: true
                baz: false
                "quoted {dict:03}": "v narekovajih {slovar:04}"
                'quoted {dict:05}': 'v narekovajih {slovar:04}'
    class `B`:
        nothing: nič
    """)
        msgs = load(fn)
        self.assertEqual(
            msgs,
            {'class `A`': MsgNode(value={
                'foo': MsgNode(value='bar'),
                'boo': MsgNode(value=None),
                'def `f`': MsgNode(value={
                    'def `g`': MsgNode(value={
                        'vaz': MsgNode(value=True),
                        'baz': MsgNode(value=False),
                        'quoted {dict:03}': MsgNode(
                            value='v narekovajih {slovar:04}'),
                        'quoted {dict:05}': MsgNode(
                            value='v narekovajih {slovar:04}')
                    })
                })
             }),
             'class `B`': MsgNode(value={
                 'nothing': MsgNode(value='nič')
             })
            })

    def test_load_jaml(self):
        fn = self.prepare_file("x.jaml", """
        class `A`:
            foo: bar: baz
        """)
        msgs = load(fn)
        self.assertEqual(
            msgs,
            {'class `A`': MsgNode(value={
                'foo': MsgNode(value='bar: baz')
            })})

    def test_loader_graceful_exit_on_error(self):
        fn = self.prepare_file("x.jaml", """
        class `A`: asdf
            foo: bar: baz
        """)
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertRaises(SystemExit, load, fn)
            self.assertIn("rror in", buf.getvalue())
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertRaises(SystemExit, load, "no such file")
            self.assertIn("not found", buf.getvalue())

    def test_loader_verifies_sanity(self):
        fn = self.prepare_file("x.jaml", """
        class `A`:
            def `foo`: bar
        """)
        self.assertRaises(SystemExit, load, fn)

    def test_check_sanity(self):
        # unexpected namespace
        check_sanity = yamlized(messages.check_sanity)
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertFalse(check_sanity(
                {"a": "b", "def `f`": {"x": {"y": "z"}}}))
            self.assertEqual(
                buf.getvalue(),
                "def `f`/x: Unexpectedly a namespace\n")
        # def is not a namespace
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertFalse(check_sanity(
                {"module": {"a": "b", "def `f`": {"def `x`": "y"}}}))
            self.assertEqual(
                buf.getvalue(),
                "module/def `f`/def `x`: Unexpectedly not a namespace\n")
        # class is not a namespace
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertFalse(check_sanity(
                {"module": {"a": "b", "def `f`": {"class `x`": "y"}}}))
            self.assertEqual(
                buf.getvalue(),
                "module/def `f`/class `x`: Unexpectedly not a namespace\n")
        # everything OK
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertTrue(check_sanity(
                {"module": {"a": "b", "def `f`": {"class `x`": {"z": "t"}}}}))
            self.assertEqual(
                buf.getvalue(),
                "")
        # check entire structure, even when there are problems
        with io.StringIO() as buf, redirect_stdout(buf):
            self.assertFalse(check_sanity(
                {"module1": {
                    "a": "b",
                    "def `f`": "t",
                    "class `x`": {
                        "z": "t",
                        "m": {"x": False}
                    },
                    "t": "o"},
                 "module2": {
                    "def `g`": None,
                    "x": "y"},
                 "module3": {
                    "a": "b"}
                },
                "somefile"))
            self.assertEqual(
                buf.getvalue(),
                """Errors in somefile:
module1/def `f`: Unexpectedly not a namespace
module1/class `x`/m: Unexpectedly a namespace
module2/def `g`: Unexpectedly not a namespace
""")

    def test_dict_msg_nodes_conversion(self):
        msg_dict = {
            "module1": {
                "a": "b",
                "class `x`": {
                    "z": None,
                    "m": {"x": False}
                },
                "t": True},
            "module2": {
                "x": "y"},
        }
        msg_nodes = {
            'module1': MsgNode(value={
                'a': MsgNode(value='b'),
                    'class `x`': MsgNode(value={
                        'z': MsgNode(value=None),
                        'm': MsgNode(value={
                            'x': MsgNode(value=False)},
                        )}),
                    't': MsgNode(value=True)},
             ),
             'module2': MsgNode(value={
                 'x': MsgNode(value='y')},
            )}
        self.assertEqual(dict_to_msg_nodes(msg_dict), msg_nodes)
        self.assertEqual(dict_from_msg_nodes(msg_nodes), msg_dict)
        self.assertEqual(
            dict_from_msg_nodes({"x": MsgNode("foo", ["bar", "baz"])}),
            {"x": "foo"})

    @patch("builtins.open")
    @patch("yaml.dump")
    @patch("trubar.jaml.dump")
    def test_dump(self, jaml_dump, yaml_dump, _):
        msgdict = {"x": MsgNode("foo", ["bar", "baz"])}
        dump(msgdict, "x.jaml")
        jaml_dump.assert_called_with(msgdict)
        jaml_dump.reset_mock()
        yaml_dump.assert_not_called()

        msgdict = {"x": MsgNode("foo", ["bar", "baz"])}
        dump(msgdict, "x.yaml")
        self.assertEqual(yaml_dump.call_args[0][0], dict_from_msg_nodes(msgdict))
        jaml_dump.assert_not_called()


if __name__ == "__main__":
    unittest.main()
