# Message Files

**TL;DR:** Look at the example from Getting Started. Read this page only if you run into problems and need details.

Messages are stored in files with extension .jaml. Jaml is a simplified version of Yaml, limited to the functionality needed by Trubar. It does not support lists, flow collections, node anchors, different datatypes... This allows for simpler syntax, in particular less quotes.

### File Structure

The first-level keys are file names, with their paths relative to the root passed in the `-s` option of `collect` and `translate`. (It is important to always use the same root for the project. Using `-s code/` wouldn't only include the strings from `setup.py`, but also prepend `sample` to the names of all scanned files!)

Lower levels have keys that

- start with `def` or `class`, and are followed by a subtree that starts in the next line,
- or represents a potentially translatable string, followed by the translation in that same line.

    There is no indication about whether a string is an f-string or not, neither does it show what kind of quotes are used in the source, because none of this matters.

Trubar also reads and writes standard yaml (it distinguishes between yaml and jaml by file extensions), but we don't recommend using it because their formatting is more complex and any comments written by translator are lost at reading.

### Translations

Translator can treat a string in approximately three ways.

- Provide a translation.
- Mark with `false` to indicate that it *must not be* translated. An example of such string is `"__main__"` or `"rb"` when calling function `open`.
- Mark it with `true`, if the strings that could be translated, but doesn't need it for this particular language or culture. A common example would be symbols like `"©️"`.
- Leave it `null` until (s)he figures out what to do with it.

The difference between `true` and `false` is important only when using this translation to [prepare templates](scenarios.md#preparing-templates) for translations into other languages.

### Comments

Comments are useful to indicate questionable translations, brainstorm with other translators or oneself, and similar. Operations on message files, like extracting and merging, keep the comments at their respective places.

A comment is always associated with some particular translation or entire function or class. It must be placed above it and conform to indendation. Comments cannot follow translations in the same line; a `#` symbol in translation is treated literally.

### Quotes

- Translation must be quoted if it

    - begins or end with space,
    - begins with a quote (single or double)
    - it is (literally) `"false"`, `"true"` or `"null"`,

(In addition, keys are quoted if they contain a colon followed by a space. But translator doesn't need to care because keys are provided by Trubar.)

Single- and double-quoted strings are treated the same. The translation must begin and end with the same type of quote. The quotes used in message files are not related to the quotes used in source code. In the introductory example, all string in code use double quotes, while some strings in the message file are single-quoted and others double quoted, for convenience.

A single-quoted string may contain double quotes and vice-versa; such quotes are treated literally. Any single (double) quotes within a single (double) quoted strings must be doubled, as in `'don''t forget to double the quotes.'`.

### Colons

Colons in translations have no special meaning. Consider the following line from the example.

```
'Wrong number: {n} is not between 5 and 20.': Napačno število: {n} ni med 5 in 20.
```

In standard yaml, the translation would need quotes because it includes a colon followed by space. In Jaml, this rule only applies to keys, which translator doesn't care about. Therefore: use colons at will.

### Multiline messages

Strings can span over multiple lines. All whitespace in multiline strings is retained.

JAML does not support any of the more complicated yaml syntax for multiline blocks.