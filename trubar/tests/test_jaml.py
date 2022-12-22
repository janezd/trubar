import unittest
from unittest.mock import patch

from trubar import jaml
from trubar.jaml import LineGenerator
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

    def test_read_blocks(self):
        text = """
class `A`:
    foo: |
            block
            translation
    a: b
    |
       block
       key
    : and a simple translation
    def `f`:
        simple key: |
                       block
                         translation
                       with spaces
    def `g`:
        |
           block key
        : |
           translation"""
        self.assertEqual(
            jaml.read(text),
            {'class `A`': MsgNode(value={
                'foo': MsgNode(value='block\ntranslation'),
                'a': MsgNode(value='b'),
                'block\nkey': MsgNode(value='and a simple translation'),
                'def `f`': MsgNode(value={
                    'simple key': MsgNode(value='block\n  translation\nwith spaces'),
                    }),
                'def `g`': MsgNode(
                    value={'block key': MsgNode(value='translation')},
                    comments=None)
            })})

        text = """
abc:
    |

def
  ghi

   jkl
mno
|||
    : ghu
    pqr: stu"""
        self.assertEqual(
            jaml.read(text),
            {'abc': MsgNode(value={
                'def\n  ghi\n\n   jkl\nmno': MsgNode(value='ghu',),
                'pqr': MsgNode(value='stu', comments=None)},)})

        text = """
abc:
    def: |
ghi

jkl
mno
|||
    pqr: stu"""
        self.assertEqual(
            jaml.read(text),
            {'abc': MsgNode(
                value={'def': MsgNode(value='ghi\n\njkl\nmno', comments=None),
                       'pqr': MsgNode(value='stu', comments=None)},
                comments=None)}
        )
        text = """
abc:
    def: | 2
        ghi

        jkl
    pqr: stu"""
        self.assertEqual(
            jaml.read(text),
            {'abc': MsgNode(
                value={'def': MsgNode(value='  ghi\n\n  jkl', comments=None),
                       'pqr': MsgNode(value='stu', comments=None)},
                comments=None)}
        )

    def test_read_backslashes(self):
        text = r"""
fo\no1: ba\nr
fo\x: ba\x
"ra\nbit": "za\njec"
"ra\\nbot": "za\\njoc"
"""
        msgs = jaml.read(text)
        self.assertEqual(msgs, {r'fo\no1': MsgNode(value=r'ba\nr', comments=None),
 r'fo\x': MsgNode(value=r'ba\x', comments=None),
 'ra\nbit': MsgNode(value='za\njec', comments=None),
 r'ra\nbot': MsgNode(value=r'za\njoc', comments=None)})

    def test_read_quotes(self):
        text = """
foo1: "bar 
foo2: bar" 
foo3: "bar" 
foo4: "ba\"r" 
foo5: 'bar 
foo6: bar' 
foo7: 'bar' 
foo8: 'ba\'r' 
foo9: 'ba\"r' 
foo10: "bar' 
foo11: "bar' 
foo12: "ba\\"r" 
foo13: 'ba\\'r' 
"""
        msgs = jaml.read(text)
        self.assertEqual([node.value for node in msgs.values()],
                         ['"bar', 'bar"', 'bar', '"ba"r"',
                          "'bar", "bar'", "bar", "'ba'r'",
                          'ba"r', "\"bar'", "\"bar'",
                          'ba"r', "ba'r"])

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

    def test_format_errors(self):
        # This function checks for exact error messages. While this is not
        # a good practice in general, it makes these tests more readable
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: block must be indented", jaml.read, """
        abc:
            |
            def
            : ghi"""
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 3: colon expected", jaml.read, """
        abc:
            def
                ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )
        self.assertRaisesRegex(
            jaml.JamlError, "Line 4: invalid quoted key", jaml.read, """
        abc:
            def:
                "ghi: jkl
            jkl: mno
        prs:
            tuv: bdf""",
        )
        self.assertRaisesRegex(
            jaml.JamlError,
            "Line 5: missing value after block key", jaml.read, """
        abc:
            |
              def
              : ghi"""
        )
        self.assertRaisesRegex(
            jaml.JamlError,
            "Line 5: value after block key must be aligned with key",
            jaml.read, """
        abc:
            |
                def
             : ghi
              """
        )
        self.assertRaisesRegex(
            jaml.JamlError,
            "Line 5: value after block key must be aligned with key",
            jaml.read, """
        abc:
            |
                def
          : ghi
              """
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

    def test_dump_blocks(self):
        tree = {"a/b.py":
                    MsgNode(
                       value={ "def `f`": MsgNode({
                           "a\nb\nc": MsgNode("abc"),
                           "abc": MsgNode("a\n" + "b" * 100),
                           "foo": MsgNode(False),
                           "def": MsgNode("a\n" + "b" * 100),
                       })}),
                "x/y.py": MsgNode(None)
                }
        self.assertEqual(jaml.dump(tree), """
a/b.py:
    def `f`:
        |
            a
            b
            c
        : abc
        abc: |
            a
            bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
        foo: false
        def: |
            a
            bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
x/y.py: null
"""[1:])


class LineGeneratorTest(unittest.TestCase):
    def test_generator(self):
        gen = LineGenerator("""
abc
    def
  ghi
"""[1:].splitlines())
        s, i = next(gen)
        self.assertEqual(s, "abc")
        self.assertEqual(i, 0)
        self.assertEqual(gen.line_no, 1)

        s, i = next(gen)
        self.assertEqual(s, "    def")
        self.assertEqual(i, 4)
        self.assertEqual(gen.line_no, 2)
        gen.put_back()
        self.assertEqual(gen.line_no, 2)
        s, i = next(gen)
        self.assertEqual(s, "    def")
        self.assertEqual(i, 4)
        self.assertEqual(gen.line_no, 2)
        gen.put_back()
        s, i = next(gen)
        self.assertEqual(s, "    def")
        self.assertEqual(i, 4)
        self.assertEqual(gen.line_no, 2)
        gen.put_back()
        gen.put_back()
        self.assertEqual(gen.line_no, 2)
        s, i = next(gen)
        self.assertEqual(s, "    def")
        self.assertEqual(i, 4)
        self.assertEqual(gen.line_no, 2)

        s, i = next(gen)
        self.assertEqual(s, "  ghi")
        self.assertEqual(i, 2)
        self.assertEqual(gen.line_no, 3)


if __name__ == "__main__":
    unittest.main()
