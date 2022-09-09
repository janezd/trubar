import os
import unittest

import libcst as cst

from trubar.actions import StringCollector, collect


class StringCollectorTest(unittest.TestCase):
    def collect(self, s):
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
            "{'foo_module': {'A': {'b': {'c': {'foo': None, 'bar': None}, 'baz': None, 'B': {'baz': None}}}, 'C': {'crux': None}}}")

    def test_module(self):
        import trubar.tests.test_module
        msgs = collect(os.path.split(trubar.tests.test_module.__file__)[0], "")
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
        import trubar.tests.test_module_2
        msgs = collect(os.path.split(trubar.tests.test_module_2.__file__)[0], "")
        self.assertEqual(
            msgs,
            {'__init__.py': {'f': {'not a docstring': None}},
             'submodule.py': {'f': {'not a docstring': None}}})

    def test_no_strings_within_interpolation(self):
        msgs = self.collect("""a = f'x = {len("foo")} {"bar"}'""")



if __name__ == "__main__":
    unittest.main()