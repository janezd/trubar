# pylint: disable=protected-access, invalid-name

import re
import io
import os
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout

import libcst as cst

from trubar.actions import \
    collect, missing, merge, template, \
    StringCollector, StringTranslator, StringTranslatorMultilingual, \
    CountImportsFromFuture, Stat, TranslationError

from trubar import config
from trubar.config import LanguageDef
from trubar.messages import dict_from_msg_nodes, dict_to_msg_nodes, MsgNode
from trubar.tests import yamlized
import trubar.tests.test_module

test_module_path = os.path.split(trubar.tests.test_module.__file__)[0]


class CountImportsFromFutureTest(unittest.TestCase):
    module_with_futures = """
'''
this is a docstring
'''

# A comment here
from __future__ import annotations

# A comment there
"And another string"
from __future__ import division
from __future__ import print_function # test here

# A comment everywhere
import os
"""

    module_without_futures = """
'''
this is a docstring
'''
# test here
# A comment here
import os

# A comment there
"And another string"
import path
 """

    def test_counts(self):
        tree = cst.parse_module(self.module_with_futures)
        cif = CountImportsFromFuture()
        tree.visit(cif)
        self.assertEqual(cif.count, 3)

        tree = cst.parse_module(self.module_without_futures)
        cif = CountImportsFromFuture()
        tree.visit(cif)
        self.assertEqual(cif.count, 0)


class StringCollectorTest(unittest.TestCase):
    @staticmethod
    def collect(s):
        collector = StringCollector()
        tree = cst.metadata.MetadataWrapper(cst.parse_module(s))
        tree.visit(collector)
        return dict_from_msg_nodes(collector.contexts[0])

    def test_simple_string(self):
        msgs = self.collect("""
def f(x):
    a = "a string"
    b = 'another string'
    c = \"\"\"and yet another\"\"\"
    d = '''and there's more'''
""")
        expected = {'def `f`': {'a string': None,
                                'another string': None,
                                'and yet another': None,
                                "and there's more": None}}
        self.assertEqual(msgs, expected)
        # order should match, too
        self.assertEqual(list(msgs["def `f`"]),
                         list(expected["def `f`"]))

    def test_formatted_string(self):
        msgs = self.collect("""
        
def f(x):
    a = f"a string {x}"
    b = f'another string {2 + 2}'
    c = f\"\"\"and yet another {3 + 3}\"\"\"
    d = f'''and there's more'''
""")
        expected = {'def `f`': {
            'a string {x}': None,
            'another string {2 + 2}': None,
            'and yet another {3 + 3}': None,
            "and there's more": None}}

        self.assertEqual(msgs, expected)
        # order should match, too
        self.assertEqual(list(msgs["def `f`"]),
                         list(expected["def `f`"]))

    def test_class_func(self):
        msgs = self.collect("""
class A:
    def b(x):
        def c(x):
            d = "foo"
            e = "bar"
        a = "baz"
        
        class B:
           f = "baz"
           
class C:
    g = "crux" 
""")

        # check structure and order, thus `repr`
        self.assertEqual(
            repr(msgs),
            "{'class `A`': {'def `b`': {'def `c`': {'foo': None, 'bar': None}, "
            "'baz': None, 'class `B`': {'baz': None}}}, 'class `C`': {'crux': None}}")

    def test_module_and_walk_and_collect(self):
        msgs, _ = collect(test_module_path, {}, "", quiet=True)
        self.assertEqual(
             dict_from_msg_nodes(msgs),
            {
             'bar_module/foo_module/__init__.py': {
                 "I've seen things you people wouldn't believe...": None},
             'bar_module/__init__.py': {
                 'Attack ships on fire off the shoulder of Orion...': None},
             'baz_module/__init__.py': {'def `f`': {
                 'I watched C-beams glitter in the dark near the Tannhäuser Gate.': None}},
             '__init__.py': {'class `Future`': {
                'All those moments will be lost in time, like tears in rain...': None,
                'Time to die.': None}},
            }
        )

    def test_no_docstrings(self):
        msgs = self.collect('''
"""docstring"""

def f(x):
    "docstring"
    a = "not a docstring"

def g(x):
    """Also docstring"""
    f("bar")
    "useless string"''')
        self.assertEqual(
            msgs,
            {'def `f`': {'not a docstring': None},
                  'def `g`': {'bar': None}})

    def test_no_strings_within_interpolation(self):
        msgs = self.collect("""a = f'x = {len("foo")} {"bar"}'""")
        self.assertEqual(msgs, {'x = {len("foo")} {"bar"}': None})


class StringTranslatorTest(unittest.TestCase):
    def test_translator(self):
        module = """
# A comment
class A:
    def b(x):  # Another comment
        def c(x):
              d = '''foo'''  # intentional bad indentation
              e = "bar"
        a = "baz"

        class B:
           f = f"baz{42}"


class C:
    g = 'crux'
"""

        translations = {'class `A`': {'def `b`': {'def `c`': {'foo': 'sea food',
                                                              'bar': None},
                                                  'baz': True,
                                                  'class `B`': {'baz{42}':
                                                                    False}}},
                        'class `C`': {'crux': ""}}

        tree = cst.parse_module(module)
        translator = yamlized(StringTranslator)(translations, tree)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        self.assertEqual(trans_source, """
# A comment
class A:
    def b(x):  # Another comment
        def c(x):
              d = '''sea food'''  # intentional bad indentation
              e = "bar"
        a = "baz"

        class B:
           f = f"baz{42}"


class C:
    g = ''
""")

    def test_auto_quote_and_prefix(self):
        module = """
print("Foo")
print('Bar')
print("2 + 2 = 4")
print("2 + 3 = 4")
print("2 + 4 = 4")
print("baz")
print("kux")
print(r"bing")
print('''f x g''')
print(\"\"\"f y g\"\"\")
print("just {braces}, not an f-string!")
"""

        tree = cst.parse_module(module)
        translations = {"Foo": 'Fo"o',
                        "Bar": "B'ar",
                        "2 + 2 = 4": "2 + 2 = {2 + 2}",
                        "2 + 3 = 4": "2 + 3 = {}",
                        "2 + 4 = 4": "2 + 4 = {not an expression}",
                        "baz": "ba{}z",
                        "kux": "ku{--}x",
                        "bing": "b{2 + 2}ng",
                        "f x g": "f ' g",
                        "f y g": 'f " g',
                        "just {braces}, not an f-string!": "samo {oklepaji}!"
                        }
        translator = yamlized(StringTranslator)(translations, tree)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        self.assertEqual(trans_source, """
print('Fo"o')
print("B'ar")
print(f"2 + 2 = {2 + 2}")
print("2 + 3 = {}")
print("2 + 4 = {not an expression}")
print("ba{}z")
print("ku{--}x")
print(fr"b{2 + 2}ng")
print('''f ' g''')
print(\"\"\"f " g\"\"\")
print("samo {oklepaji}!")
""")

    def test_syntax_error(self):
        tree = cst.parse_module("print('foo')")
        translator = yamlized(StringTranslator)({"foo": 'bar\nbaz'}, tree)
        self.assertRaisesRegex(
            TranslationError,
            re.compile(".*foo.*bar.*", re.DOTALL), tree.visit, translator)

    def test_import_from_future(self):
        module = CountImportsFromFutureTest.module_with_futures
        imports = "import plural\nimport dual"
        auto_import = cst.parse_module(imports).body
        tree = cst.parse_module(module)
        translator = StringTranslator({}, tree, auto_import, 3)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        self.assertEqual(
            trans_source,
            module.replace(
                "test here\n",
                "test here\nimport plural\nimport dual\n")
        )

        module = CountImportsFromFutureTest.module_without_futures
        imports = "import plural\nimport dual"
        auto_import = cst.parse_module(imports).body
        tree = cst.parse_module(module)
        translator = StringTranslator({}, tree, auto_import, 0)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        self.assertEqual(
            trans_source,
            module.replace(
                "# test here\n",
                "import plural\nimport dual\n# test here\n")
        )


class StringTranslatorMultilingualTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        config.config.languages = {
            "de": LanguageDef("Deutsch", "German", True),
            "si": LanguageDef("Slovenščina", "Slovenian", False),
            "en": LanguageDef("English", "English", False)}

    def tearDown(self):
        config.config.languages = None

    def _translate(self, module, messages, add_initial=False):
        tree = cst.parse_module(module)
        message_tables = [["msg1", "msg2", "msg3"],
                          ["msg4", "msg5", "msg6"],
                          ["msg7", "msg8", "msg8"]] if add_initial else [[], [], []]
        translator = StringTranslatorMultilingual(
            [{}] + [dict_to_msg_nodes(d) for d in messages],
            message_tables,
            tree)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        return trans_source, message_tables

    def test_translator(self):
        module = """
# A comment
class A:
    def b(x):  # Another comment
        def c(x):
              d = '''foo'''  # intentional bad indentation
              e = "bar"
        a = "baz"

        class B:
           f = f"baz{42}"


class C:
    g = 'crux'
"""

        trans_foo = {'class `A`': {'def `b`': {'def `c`': {'foo': 'sea food',
                                                           'bar': None},
                                               'baz': True,
                                               'class `B`': {'baz{42}': False}}},
                     'class `C`': {'crux': ""}}

        trans_fee = {'class `A`': {'def `b`': {'def `c`': {'bar': "no-bar"},
                                               'class `B`': {'baz{42}': "bar(1)"}}}}

        trans_source, message_tables = self._translate(
            module, [trans_foo, trans_fee], True)
        self.assertEqual(trans_source, """
# A comment
class A:
    def b(x):  # Another comment
        def c(x):
              d = _tr.m[3, '''foo''']  # intentional bad indentation
              e = _tr.m[4, "bar"]
        a = "baz"

        class B:
           f = _tr.e(_tr.c(5, "baz{42}"))


class C:
    g = _tr.m[6, 'crux']
""")
        self.assertEqual(
            message_tables,
            [['msg1', 'msg2', 'msg3', 'foo', 'bar', 'f"baz{42}"', 'crux'],
             ['msg4', 'msg5', 'msg6', 'sea food', 'bar', 'f"baz{42}"', ''],
             ['msg7', 'msg8', 'msg8', 'foo', 'no-bar', 'f"bar(1)"', 'crux']]
        )

    def test_f_string_languages(self):
        node = Mock()
        m = StringTranslatorMultilingual._f_string_languages

        node.prefix = "f"
        node.quote = "'"
        # Original is an f-string - don't add
        self.assertEqual(m(node, ["a string", "one", "two{x}"]), [])

        node.prefix = ""
        m = StringTranslatorMultilingual._f_string_languages
        # No language needs it
        self.assertEqual(m(node, ["a string", "one", "two"]),
                         [])

        # English needs it
        self.assertEqual(m(node, ["a string", "one", "two{x}"]),
                         ["English (two{x})"])
        # Slovenian and English needs it
        self.assertEqual(m(node, ["a string", "one{y}", "two{x}"]),
                         ["Slovenian (one{y})", "English (two{x})"])
        # Original is not an f-string, but has {},
        # hence translations are supposed to have them without being f-strings
        self.assertEqual(m(node, ["a string{x}", "one{y}", "two{x}"]),
                         [])

        for quote in ['"', "'", "'''", '"""']:
            self.assertEqual(m(node, ["a string", "one", f"t{quote}wo{{x}}"]),
                             [f"English (t{quote}wo{{x}})"])

        # No smart quotes
        with patch("trubar.config.config.smart_quotes", False):
            self.assertEqual(
                m(node, ["a string", "on'e", "tw'o{x}"]),
                [])

    def test_get_quote(self):
        node = Mock()
        m = StringTranslatorMultilingual._get_quote

        node.prefix = ""
        node.quote = '"'
        self.assertEqual(
            m(node, "'a string'", ["a string", "one", "two{x}"],
              "", ["English"]),
            '"')

        node.quote = "'''"
        self.assertEqual(
            m(node, "'a string'", ["a string", "one", "two{x}"],
              "", ["English"]),
            "'''")

        node.quote = "'"
        self.assertEqual(
            m(node, "'a string'", ["a string", "one", "two{x}"],
              "", ["English"]),
            "'")

        node.quote = "'"
        self.assertEqual(
            m(node, "'a string'", ["a string", "one", "tw'o{x}"],
              "", ["English"]),
            '"')

        node.quote = "'"
        self.assertEqual(
            m(node, "'a str'ing'", ["a str'ing", "one", "two{x}"],
              "", ["English"]),
            '"')

        node.quote = "'"
        self.assertEqual(
            m(node, "'a str'ing'", ["a str'ing", "on\"e", "two{x}"],
              "", ["English"]),
            "'''")

        node.quote = "'"
        self.assertEqual(
            m(node, "'a str'''ing'", ["a str'''ing", "on\"e", "two{x}"],
              "", ["English"]),
            '"""')

        node.quote = "'"
        self.assertRaises(
            TranslationError,
            m, node, "'a str'''ing'", ["a str'''ing", "one", "tw\"\"\"o{x}"],
            "", ["English"])

        with patch("trubar.config.config.smart_quotes", False):
            node.quote = "'"
            self.assertRaises(
                TranslationError,
                m, node, "'a str'ing'", ["a str'ing", "one", "two{x}"],
                "", ["English"])

            node.quote = "'"
            self.assertRaises(
                TranslationError,
                m, node, "'a str'''ing'", ["a str'''ing", "one", "tw\"\"\"o{x}"],
                "", ["English"])

    def test_auto_prefix(self):
        # No f-strings, no problems
        translation, tables = self._translate(
            "print('foo')", [{"foo": "don't"}, {"foo": 'x"y'}])
        self.assertEqual(translation, "print(_tr.m[0, 'foo'])")
        self.assertEqual(tables, [["foo"], ["don't"], ['x"y']])

        # Original is an f-string, and so is one of translations, other is missing
        translation, tables = self._translate(
            "print(f'fo{o}')", [{"fo{o}": "do{n}t"}, {}])
        self.assertEqual(translation, "print(_tr.e(_tr.c(0, 'fo{o}')))")
        self.assertEqual(tables, [["f'fo{o}'"], ["f'do{n}t'"], ["f'fo{o}'"]])

        # Original is an f-string, translations are not
        translation, tables = self._translate(
            "print(f'fo{o}')", [{"fo{o}": "dont"}, {}])
        self.assertEqual(translation, "print(_tr.e(_tr.c(0, 'fo{o}')))")
        self.assertEqual(tables, [["f'fo{o}'"], ["f'dont'"], ["f'fo{o}'"]])

        # Original is not an f-string, one of translations is
        translation, tables = self._translate(
            "print('foo')", [{"foo": "do{n}t"}, {"foo": "bar"}])
        self.assertEqual(translation, "print(_tr.e(_tr.c(0, 'foo')))")
        self.assertEqual(tables, [["f'foo'"], ["f'do{n}t'"], ["f'bar'"]])

        with patch("trubar.config.config.auto_prefix", False):
            translation, tables = self._translate(
                "print('foo')", [{"foo": "do{n}t"}, {"foo": "bar"}])
            self.assertEqual(translation, "print(_tr.m[0, 'foo'])")
            self.assertEqual(tables, [['foo'], ['do{n}t'], ['bar']])

    def test_smart_quotes_and_f(self):
        # Original has an f-string, and translations have different quotes
        translation, tables = self._translate(
            "print(f'foo')", [{"foo": "don't"}, {"foo": 'x"y'}])
        self.assertEqual(translation, "print(_tr.e(_tr.c(0, 'foo')))")
        self.assertEqual(
            tables,
            [["f'''foo'''"], ["f'''don't'''"], ["f'''x\"y'''"]])

        # One language has an f-string, and translations have different quotes
        self._translate(
          "print('foo')", [{"foo": "d{o}n't"}, {"foo": 'x"y'}])
        self.assertEqual(translation, "print(_tr.e(_tr.c(0, 'foo')))")
        self.assertEqual(
            tables,
            [["f'''foo'''"], ["f'''don't'''"], ["f'''x\"y'''"]])

        with patch("trubar.config.config.smart_quotes", False):
            # Mismatching quotes
            self.assertRaises(
                TranslationError,
                self._translate, "print(f'foo')", [{"foo": "do{n}'t"}, {}])

            # Original has an f-string, but quotes are OK
            translation, tables = self._translate(
                'print(f"foo")', [{"foo": "don't"}, {"foo": "x'y"}])
            self.assertEqual(translation, 'print(_tr.e(_tr.c(0, "foo")))')
            self.assertEqual(tables, [['f"foo"'], ['f"don\'t"'], ['f"x\'y"']])

    def test_syntax_error(self):
        tree = cst.parse_module("print('foo')")
        translator = yamlized(StringTranslator)({"foo": 'bar\nbaz'}, tree)
        self.assertRaisesRegex(
            TranslationError,
            re.compile(".*foo.*bar.*", re.DOTALL), tree.visit, translator)


class ActionsTest(unittest.TestCase):
    @patch("builtins.print")
    def test_collect(self, print_):
        def parse_file(fn):
            c = fn[-4]
            return MsgNode(dict_to_msg_nodes(
                {f"def `{c}`": {f"{c}{c}": None,
                                f"{c}{c}{c}": None},
                 f"{c}": None}))
        file_list = [("a.py", "x/a.py"),
                     ("b/c.py", "x/b/c.py"),
                     ("b/d.py", "x/b/d.py")]
        with patch("trubar.actions.StringCollector.parse_file", parse_file), \
                patch("trubar.actions.walk_files", Mock(return_value=file_list)):
            mess, remo = collect("", {}, "", quiet=True)
            self.assertEqual(
                mess,
                dict_to_msg_nodes({
                    "a.py": {"def `a`": {"aa": None, "aaa": None}, "a": None},
                    "b/c.py": {"def `c`": {"cc": None, "ccc": None}, "c": None},
                    "b/d.py": {"def `d`": {"dd": None, "ddd": None}, "d": None},
                })
            )
            self.assertEqual(remo, {})
            print_.assert_not_called()

            collect("", {}, "", quiet=False)
            print_.assert_called()
            print_.reset_mock()

            existing = dict_to_msg_nodes({
                "b/d.py": {"def `d`": {"dd": "dtrans", "ddd": None},
                           "foo": None, "bar": "baz"},
                "b/e.py": {"qux": None},
                "b/f.py": {"qui": "quo"}})
            mess, remo = collect("", deepcopy(existing), "", quiet=True)
            self.assertEqual(
                mess,
                dict_to_msg_nodes({
                    "a.py": {"def `a`": {"aa": None, "aaa": None}, "a": None},
                    "b/c.py": {"def `c`": {"cc": None, "ccc": None}, "c": None},
                    "b/d.py": {"def `d`": {"dd": "dtrans", "ddd": None}, "d": None},
                })
            )
            self.assertEqual(
                remo,
                dict_to_msg_nodes({
                    "b/d.py": {"bar": "baz"},
                    "b/f.py": {"qui": "quo"}
                })
            )
            print_.assert_not_called()

            existing = dict_to_msg_nodes({
                "b/d.py": {"def `d`": {"dd": "dtrans", "ddd": None},
                           "foo": None, "bar": "baz"},
                "b/e.py": {"qux": None},
                "b/f.py": {"qui": "quo"},
                "b/g.py": {"qux": None},
                "b/h.py": {"qui": "quo"},
            })
            file_list += [("b/e.py", "x/b/e.py"),
                          ("b/f.py", "x/b/f.py")]
            mess, remo = collect("", deepcopy(existing), "d", quiet=True)
            self.assertEqual(
                mess,
                dict_to_msg_nodes({
                    "b/d.py": {"def `d`": {"dd": "dtrans", "ddd": None}, "d": None},
                    "b/e.py": {"qux": None},
                    "b/f.py": {"qui": "quo"}
                })
            )
            self.assertEqual(
                remo,
                dict_to_msg_nodes({
                    "b/d.py": {"bar": "baz"},
                    "b/h.py": {"qui": "quo"}
                })
            )
            print_.assert_not_called()

    @patch("builtins.print")
    def test_collect_empty_file(self, _):
        def parse_file(fn):
            if fn == "a.py":
                return MsgNode({"x": MsgNode(None)})
            else:
                return MsgNode({})
        file_list = [("a.py", "a.py"),
                     ("b.py", "b.py")]
        with patch("trubar.actions.StringCollector.parse_file", parse_file), \
                patch("trubar.actions.walk_files", Mock(return_value=file_list)):
            mess, _ = collect("", {}, "", quiet=True)
            self.assertEqual(mess, dict_to_msg_nodes({"a.py": {"x": None}}))


    # translate: we test walk and StringTranslator; let us assume we call them
    # correctly

    def test_missing_structure(self):
        translations = {
            "a": "b",
            "c": None,
            "d": False,
            "e": True,
            "class `f`": {
                "g": "h",
                "i": False,
                "j": None,
                "k": True},
            "k": "l",
            "def `m`": {"n": "o"},
            "class `p`": {"q": "r"}
        }
        messages = {
            "a": None,
            "c": None,
            "d": None,
            "e": None,
            "class `f`": {
                "g": None,
                "i": None,
                "j": None,
                "k": None},
            "def `k`": {"p": None},
            "m": None,
            "class `p`": {"q": None},
            "s": None,
            "def `t`": {"u": None}
        }
        self.assertEqual(
            yamlized(missing)(translations, messages),
            {"c": None,
             "class `f`": {"j": None},
             "def `k`": {"p": None},
             "m": None,
             "s": None,
             "def `t`": {"u": None}
             }
        )

    def test_missing_pattern(self):
        # test that pattern is applied to first level only
        messages = {
            "foo_1": {"foo_2": "x", "a": {"b": "c"}},
            "2_foo": {"a": {"b": "c"}},
            "bar": {"foo_1": {"b": "c"}}
        }
        self.assertEqual(
            yamlized(missing)({}, messages, "foo"),
            {"foo_1": {"foo_2": "x", "a": {"b": "c"}},
             "2_foo": {"a": {"b": "c"}}}
        )

    def test_merge(self):
        existing = dict_to_msg_nodes({
            "a": None,
            "c": "not-none",
            "d": "x",
            "e": "y",
            "class `f`": {
                "g": "z",
                "i": None,
                "def `j`": {"a": None},
                "k": None},
            "def `k`": {"p": None},
            "m": None,
            "class `p`": {"q": None},
            "s": None,
            "def `t`": {"u": "v"}
        })
        additional = dict_to_msg_nodes({
            "a": "b",
            "c": None,
            "d": False,
            "e": True,
            "class `f`": {
                "g": "h",
                "i": False,
                "j": "r",
                "x": "y",
                "k": True},
            "k": None,
            "def `m`": {"u": "v"},
            "class `p`": {"q": "r"},
            "def `no_trans`": {"x": None, "y": False}
        })
        with io.StringIO() as buf, redirect_stdout(buf):
            removed = merge(additional, existing)
            printed = buf.getvalue()

        self.assertEqual(
            dict_from_msg_nodes(existing),
            {"a": "b",
             "c": "not-none",
             "d": False,
             "e": True,
             "class `f`": {"g": "h",
                 "i": False,
                 "def `j`": {"a": None},
                 "k": True},
             "def `k`": {"p": None},
             "m": None,
             "class `p`": {"q": "r"},
             "s": None,
             "def `t`": {"u": "v"}
            }
        )
        removed = dict_from_msg_nodes(removed)
        self.assertEqual(set(removed), {"class `f`", "def `m`"})
        self.assertEqual(set(removed["class `f`"]), {"x", "j"})
        self.assertEqual(printed,
                         """class `f`/j not in target structure
class `f`/x not in target structure
def `m` not in target structure
""")

        with io.StringIO() as buf, redirect_stdout(buf):
            merge(additional, existing, print_unused=False)
            printed = buf.getvalue()
            self.assertEqual(printed, "")

    def test_template(self):
        messages = {
            "a": "b",
            "c": False,
            "d": True,
            "e": None,
            "f": { "g": "h", "i": False},
            "j": { "k": False, "l": {"m": False, "n": False}}
        }
        self.assertEqual(
            yamlized(template)(messages),
           {"a": None,
            "d": None,
            "e": None,
            "f": { "g": None}
        }
        )
        self.assertEqual(yamlized(template)(messages, "f"), {"f": {"g": None}})
        self.assertEqual(yamlized(template)(messages, "g"), {})

    def test_stat(self):
        messages = {
            "a": "b",
            "c": "not-none",
            "d": False,
            "e": True,
            "class `foo`": {
                "g": "h",
                "i": False,
                "def `j`": {
                    "a": None},
                "k": True},
            "def `k`": {"p": None},
            "m": None,
            "class `p`": {"q": "r"},
            "s": None,
            "def `t`": {"u": "v"}
        }
        stat = yamlized(Stat.collect_stat)(messages)
        self.assertEqual(stat, Stat(5, 2, 4, 2))
        self.assertEqual(abs(stat), 13)

        stat = yamlized(Stat.collect_stat)({})
        self.assertEqual(stat, Stat(0, 0, 0, 0))
        self.assertEqual(abs(stat), 0)


if __name__ == "__main__":
    unittest.main()
