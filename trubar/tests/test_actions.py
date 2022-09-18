import io
import os
import unittest
from contextlib import redirect_stdout

import libcst as cst

from trubar.actions import \
    StringCollector, StringTranslator, walk_files, \
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
        expected = {'foo_module': {'f': {'a string': None,
                                         'another string': None,
                                         'and yet another': None,
                                         "and there's more": None,}}}
        self.assertEqual(msgs, expected)
        # order should match, too
        self.assertEqual(list(msgs["foo_module"]["f"]),
                         list(expected["foo_module"]["f"]))

    def test_formatted_string(self):
        msgs = self.collect("""
        
def f(x):
    a = f"a string {x}"
    b = f'another string {2 + 2}'
    c = f\"\"\"and yet another {3 + 3}\"\"\"
    d = f'''and there's more'''
""")
        expected = {'foo_module': {'f': {'a string {x}': None,
                                         'another string {2 + 2}': None,
                                         'and yet another {3 + 3}': None,
                                         "and there's more": None}}}

        self.assertEqual(msgs, expected)
        # order should match, too
        self.assertEqual(list(msgs["foo_module"]["f"]),
                         list(expected["foo_module"]["f"]))

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
            "{'foo_module': {'A': {'b': {'c': {'foo': None, 'bar': None}, "
            "'baz': None, 'B': {'baz': None}}}, 'C': {'crux': None}}}")

    def test_module_and_walk_and_collect(self):
        msgs = collect(test_module_path, "", quiet=True)
        self.assertEqual(
            msgs,
            {
             'bar_module/foo_module/__init__.py': {
                 "I've seen things you people wouldn't believe...": None},
             'bar_module/__init__.py': {
                 'Attack ships on fire off the shoulder of Orion...': None},
             'baz_module/__init__.py': {'f': {
                 'I watched C-beams glitter in the dark near the Tannhäuser Gate.': None}},
             '__init__.py': {'Future': {
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
            {'foo_module': {'f': {'not a docstring': None},
                            'g': {'bar': None}}})

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

        translations = {'A': {'b': {'c': {'foo': 'sea food',
                                          'bar': None},
                                    'baz': True,
                                    'B': {'baz{42}': False}}},
                        'C': {'crux': ""}}

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
            "f": {"g": "h",
                  "i": False,
                  "j": None,
                  "k": True},
            "k": "l",
            "m": {"n": "o"},
            "p": {"q": "r"}
        }
        messages = {
            "a": None,
            "c": None,
            "d": None,
            "e": None,
            "f": {"g": None,
                  "i": None,
                  "j": None,
                  "k": None},
            "k": {"p": None},
            "m": None,
            "p": {"q": None},
            "s": None,
            "t": {"u": None}
        }
        self.assertEqual(
            missing(translations, messages),
            {"c": None,
             "f": {"j": None},
             "k": {"p": None},
             "m": None,
             "s": None,
             "t": {"u": None}
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
            "f": {"g": "z",
                  "i": None,
                  "j": {"a": None},
                  "k": None},
            "k": {"p": None},
            "m": None,
            "p": {"q": None},
            "s": None,
            "t": {"u": "v"}
        }
        additional = {
            "a": "b",
            "c": None,
            "d": False,
            "e": True,
            "f": {"g": "h",
                  "i": False,
                  "j": "r",
                  "x": "y",
                  "k": True},
            "k": None,
            "m": {"u": "v"},
            "p": {"q": "r"}
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
             "f": {"g": "h",
                   "i": False,
                   "j": {"a": None},
                   "k": True},
             "k": {"p": None},
             "m": None,
             "p": {"q": "r"},
             "s": None,
             "t": {"u": "v"}
            }
        )
        self.assertEqual(set(removed), {"f", "k", "m"})
        self.assertEqual(set(removed["f"]), {"x", "j"})
        self.assertEqual(printed,
                         """f/j: targe is namespace, source gives a message; rejected
f/x: not in target structure; rejected
k: targe is namespace, source gives a message; rejected
m: target is message, source gives namespace; rejected
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
