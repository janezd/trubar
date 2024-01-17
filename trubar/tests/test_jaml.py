import unittest
from unittest.mock import patch

from trubar import jaml
from trubar.messages import MsgNode


class JamlReaderTest(unittest.TestCase):
    def test_read(self):
        text = """
# jaml file
class `A`:
    foo: bar
    boo: null
    # This function contains nothing but another function
    def `f`:
    
        def `g`:
            # I think that vaz is just
            # mistyped baz
            
            vaz: true
            baz: false
            "quoted {dict:03}": "v narekovajih {slovar:04}"
            'quoted {dict:05}': 'v narekovajih {slovar:04}'
            'quoted {dict:06}': v narekovajih {slovar:04}
            "This is so: so": to je tako: tako
# Yet another class
class `B`:
    nothing: nič
"""
        msgs = jaml.read(text)
        self.assertEqual(
            msgs,
            {'class `A`': MsgNode(comments=["# jaml file"], value={
                'foo': MsgNode(value='bar'),
                'boo': MsgNode(value=None),
                'def `f`': MsgNode(
                    comments=['# This function contains nothing '
                              'but another function'],
                    value={
                        'def `g`': MsgNode(value={
                            'vaz': MsgNode(
                                comments=['# I think that vaz is just',
                                          '# mistyped baz'],
                                value=True),
                            'baz': MsgNode(value=False),
                            'quoted {dict:03}': MsgNode(
                                value='v narekovajih {slovar:04}'),
                            'quoted {dict:05}': MsgNode(
                                value='v narekovajih {slovar:04}'),
                            'quoted {dict:06}': MsgNode(
                                value='v narekovajih {slovar:04}'),
                            'This is so: so': MsgNode(
                                value='to je tako: tako')
                        })
                    }
                )
             }),
             'class `B`': MsgNode(
                 comments=['# Yet another class'],
                 value={'nothing': MsgNode(value='nič')
             })
            })

    def test_read_empty_file(self):
        self.assertRaisesRegex(jaml.JamlError, "unexpected end", jaml.read, "")

    def test_read_quoted_blocks(self):
        self.assertEqual(jaml.read('''a/b.py:
    def `f`:
        "a
b
c": abc
        abc: "
     a
''' + " " * 5 + '''
   bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
"
        foo: false
        def: "a
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
x/y.py: null
        '''),
         {"a/b.py":
             MsgNode(
                 value={"def `f`": MsgNode({
                     "a\nb\nc": MsgNode("abc"),
                     "abc": MsgNode(
                         "\n     a\n     \n   " + "b" * 100 + "\n"),
                     "foo": MsgNode(False),
                     "def": MsgNode("a\n" + "b" * 100),
                 })}),
             "x/y.py": MsgNode(None)
         }
    )

    def test_read_quotes_in_values(self):
        text = '''
foo1: "bar"
foo2: """bar"
foo4: "ba""r"
foo5: "bar"""
foo7: 'bar' 
foo8: 'ba''r' 
foo9: 'ba"r'
foo12: "bar''" 
'''
        msgs = jaml.read(text)
        self.assertEqual(
            [node.value for node in msgs.values()],
            ["bar", "\"bar", "ba\"r", "bar\"", "bar", "ba'r", 'ba"r', "bar''"])

    def test_read_quotes_in_keys(self):
        text = """
1bar": foo2
"2bar": foo3
"3ba""r": foo4
4bar': foo6
'5bar': foo7
'6ba''r': foo8
"7ba""r": foo12
'8ba''r': foo13
"""
        msgs = jaml.read(text)
        self.assertEqual(
            list(msgs),
            ['1bar"', '2bar', '3ba"r', "4bar'", "5bar", "6ba'r", '7ba"r', "8ba'r"])

    def test_read_colons_in_keys(self):
        text = """
bar:baz: foo1
bar: baz: foo2
"bar:baz: boz": foo3
"bar"": baz: boz": foo4
        """
        msgs = jaml.read(text)
        self.assertEqual(
            list(msgs),
            ["bar:baz", "bar", "bar:baz: boz", "bar\": baz: boz"]
        )

    def test_stray_comments(self):
        self.assertRaisesRegex(jaml.JamlError, "5", jaml.read, """
class `A`:
    def `f`:
        sth: sth
        # stray comment
    def `g`:
        sth:stg
        """)
        self.assertRaisesRegex(jaml.JamlError, "4", jaml.read, """
class `A`:
    def `f`:
        # stray comment""")
        self.assertRaisesRegex(jaml.JamlError, "4", jaml.read, """
class `A`:
    def `f`:
        # stray comment
""")
        self.assertRaisesRegex(jaml.JamlError, "4", jaml.read, """
class `A`:
    def `f`:
        # stray comment
                
                
""")

    def test_indentation_errors(self):
        # This function checks for exact error messages. While this is not
        # a good practice in general, it makes these tests more readable
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: unexpected indent", jaml.read, """
        abc:
            def: fgh
                ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: unindent does not match any outer level",
            jaml.read, """
        abc:
            def: fgh
          ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: unindent does not match any outer level",
            jaml.read, """
        abc:
            def: fgh
ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: unindent does not match any outer level",
            jaml.read, """
        abc:
            def: fgh
ghi: jkl
            jkl: mno
        prs:
            tuv:""",
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 9: unexpected end of file", jaml.read, """
        abc:
            def: fgh
            ghi: jkl
            jkl: mno
        prs:
            tuv:
            
            """,
        )

    def test_syntax_errors(self):
        self.assertRaisesRegex(
            jaml.JamlError, "Line 1: file ends.*", jaml.read, "'''x: y")
        self.assertRaisesRegex(
            jaml.JamlError, "Line 1: file ends.*", jaml.read, "'x: y")
        self.assertRaisesRegex(
            jaml.JamlError, "Line 2: quoted key must be followed .*",
            jaml.read, '"x\ny"\na:b')
        self.assertRaisesRegex(
            jaml.JamlError, "Line 2: quoted value must be followed .*",
            jaml.read, 'x: "\na": b')
        self.assertRaisesRegex(
            jaml.JamlError,
            "Line 1: colon at the end of the key should be "
            "followed by a space or a new line", jaml.read, "x:y")

    def test_format_errors(self):
        # This function checks for exact error messages. While this is not
        # a good practice in general, it makes these tests more readable
        self.assertRaisesRegex(
            jaml.JamlError, "Line 3: key followed by colon expected", jaml.read, """
        abc:
            def
                ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: file ends", jaml.read, """
        abc:
            def:
                "ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )

    @patch("trubar.jaml.read")
    def test_readfile(self, read):
        jaml.readfile(jaml.__file__)
        with open(jaml.__file__, encoding="utf-8") as f:
            read.assert_called_with(f.read())


class JamlDumperTest(unittest.TestCase):
    def test_dump(self):
        tree = {"a/b.py":
                    MsgNode(comments=["# a few", "# initial comments"],
                       value={ "def `f`":
                                   MsgNode(comments=["# a function!"],
                                           value={"foo": MsgNode("bar"),
                                                  "baz": MsgNode(None, ["# eh"])}),
                               "yada": MsgNode(comments=["# bada", "# boom"],
                                               value=True),
                               "": MsgNode(""),
                               }),
                "class `A`":
                    MsgNode(value=False)}

        self.assertEqual(
            jaml.dump(tree),
            """
# a few
# initial comments
a/b.py:
    # a function!
    def `f`:
        foo: bar
        # eh
        baz: null
    # bada
    # boom
    yada: true
    '': ""
class `A`: false
"""[1:])

    def test_backslashes(self):
        self.assertEqual(jaml.dump({r"a\nb": MsgNode(r"c\nd")}).strip(),
                         r"a\nb: c\nd")

    def test_dump_quotes(self):
        self.assertEqual(jaml.dump({"'foo'": MsgNode("'asdf'")}),
                         """"'foo'": "'asdf'"\n""")
        self.assertEqual(jaml.dump({'"foo"': MsgNode('"asdf"')}),
                         """'"foo"': '"asdf"'\n""")
        self.assertEqual(jaml.dump({"'foo": MsgNode("asdf'")}),
                         """\"'foo": asdf'\n""")

    def test_dump_spaces_in_value(self):
        self.assertEqual(jaml.dump({"foo": MsgNode("bar ")}),
                         "foo: 'bar '\n")
        self.assertEqual(jaml.dump({"foo": MsgNode(" bar")}),
                         "foo: ' bar'\n")

    def test_quoting_keys(self):
        self.assertEqual(jaml.dump({"| ": MsgNode(True)}),
                         "'| ': true\n")
        self.assertEqual(jaml.dump({"# ": MsgNode(True)}),
                         "'# ': true\n")
        self.assertEqual(jaml.dump({" x": MsgNode(True)}),
                         "' x': true\n")
        self.assertEqual(jaml.dump({"x ": MsgNode(True)}),
                         "'x ': true\n")
        self.assertEqual(jaml.dump({" x: y": MsgNode(True)}),
                         "' x: y': true\n")
        self.assertEqual(jaml.dump({"x:y": MsgNode(True)}),
                         "x:y: true\n")

    def test_dump_blocks(self):
        tree = {"a/b.py":
                    MsgNode(
                       value={ "def `f`": MsgNode({
                           "a\nb\nc": MsgNode("abc"),
                           "abc": MsgNode("\n     a\n     \n   " + "b" * 100 + "\n"),
                           "foo": MsgNode(False),
                           "def": MsgNode("a\n" + "b" * 100),
                       })}),
                "x/y.py": MsgNode(None)
                }
        self.assertEqual(jaml.dump(tree), '''a/b.py:
    def `f`:
        'a
b
c': abc
        abc: '
     a
''' + " " * 5 + '''
   bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
'
        foo: false
        def: 'a
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
x/y.py: null
''')


if __name__ == "__main__":
    unittest.main()
