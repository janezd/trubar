import io
import os
import unittest
from contextlib import redirect_stdout

import libcst as cst

from trubar.actions import \
    StringCollector, StringTranslator, walk_files, check_sanity, \
    collect, missing, merge, template

import trubar.tests.test_module

test_module_path = os.path.split(trubar.tests.test_module.__file__)[0]


class StringCollectorTest(unittest.TestCase):
    @staticmethod
    def collect(s):
        collector = StringCollector()
        tree = cst.metadata.MetadataWrapper(cst.parse_module(s))
        collector.open_module("foo_module")
        tree.visit(collector)
        return collector.contexts[0]

    def test_simple_string(self):
        msgs = self.collect("""
def f(x):
    a = "a string"
    b = 'another string'
    c = \"\"\"and yet another\"\"\"
    d = '''and there's more'''
""")
        expected = {'foo_module': {'def `f`': {'a string': None,
                                               'another string': None,
                                               'and yet another': None,
                                               "and there's more": None}}}
        self.assertEqual(msgs, expected)
        # order should match, too
        self.assertEqual(list(msgs["foo_module"]["def `f`"]),
                         list(expected["foo_module"]["def `f`"]))

    def test_formatted_string(self):
        msgs = self.collect("""
        
def f(x):
    a = f"a string {x}"
    b = f'another string {2 + 2}'
    c = f\"\"\"and yet another {3 + 3}\"\"\"
    d = f'''and there's more'''
""")
        expected = {'foo_module': {'def `f`': {
            'a string {x}': None,
            'another string {2 + 2}': None,
            'and yet another {3 + 3}': None,
            "and there's more": None}}}

        self.assertEqual(msgs, expected)
        # order should match, too
        self.assertEqual(list(msgs["foo_module"]["def `f`"]),
                         list(expected["foo_module"]["def `f`"]))

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
            "{'foo_module': {'class `A`': {'def `b`': {'def `c`': {'foo': None, 'bar': None}, "
            "'baz': None, 'class `B`': {'baz': None}}}, 'class `C`': {'crux': None}}}")

    def test_module_and_walk_and_collect(self):
        msgs = collect(test_module_path, "", quiet=True)
        self.assertEqual(
            msgs,
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
            {'foo_module': {'def `f`': {'not a docstring': None},
                            'def `g`': {'bar': None}}})

    def test_no_strings_within_interpolation(self):
        msgs = self.collect("""a = f'x = {len("foo")} {"bar"}'""")
        self.assertEqual(
            msgs,
            {'foo_module': {'x = {len("foo")} {"bar"}': None}})


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
        translator = StringTranslator(translations, tree)
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
print("baz")
print("kux")
print(r"bing")
print('''f x g''')
print(\"\"\"f y g\"\"\")
"""

        tree = cst.parse_module(module)
        translations = {"Foo": 'Fo"o',
                        "Bar": "B'ar",
                        "2 + 2 = 4": "2 + 2 = {2 + 2}",
                        "baz": "ba{}z",
                        "kux": "ku{--}x",
                        "bing": "b{2 + 2}ng",
                        "f x g": "f ' g",
                        "f y g": 'f " g',
                        }
        translator = StringTranslator(translations, tree)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        self.assertEqual(trans_source, """
print('Fo"o')
print("B'ar")
print(f"2 + 2 = {2 + 2}")
print("ba{}z")
print("ku{--}x")
print(rf"b{2 + 2}ng")
print('''f ' g''')
print(\"\"\"f " g\"\"\")
""")


class UtilsTest(unittest.TestCase):
    def test_walk_files(self):
        tmp = test_module_path
        self.assertEqual(
            set(walk_files(tmp, skip_nonpython=True)),
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
                set(walk_files(".", skip_nonpython=True)),
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
                set(walk_files(".", "bar", skip_nonpython=True)),
                {('bar_module/__init__.py',
                  './bar_module/__init__.py'),
                 ('bar_module/foo_module/__init__.py',
                  './bar_module/foo_module/__init__.py')}
            )
        finally:
            os.chdir(old_path)

        self.assertEqual(
            set(walk_files(tmp, skip_nonpython=False)),
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

    def test_check_sanity(self):
        # unexpected namespace
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


class ActionsTest(unittest.TestCase):
    # collect is already tested above
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
            missing(translations, messages),
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
            missing({}, messages, "foo"),
            {"foo_1": {"foo_2": "x", "a": {"b": "c"}},
             "2_foo": {"a": {"b": "c"}}}
        )

    def test_merge(self):
        existing = {
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
        }
        additional = {
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
            "class `p`": {"q": "r"}
        }
        with io.StringIO() as buf, redirect_stdout(buf):
            removed = merge(additional, existing)
            printed = buf.getvalue()

        self.assertEqual(
            existing,
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
        self.assertEqual(set(removed), {"class `f`", "k", "def `m`"})
        self.assertEqual(set(removed["class `f`"]), {"x", "j"})
        self.assertEqual(printed,
                         """class `f`/j not in target structure
class `f`/x not in target structure
k not in target structure
def `m` not in target structure
""")

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
            template(messages),
           {"a": None,
            "d": None,
            "e": None,
            "f": { "g": None}
        }
        )
        self.assertEqual(template(messages, "f"), {"f": {"g": None}})
        self.assertEqual(template(messages, "g"), {})


if __name__ == "__main__":
    unittest.main()
