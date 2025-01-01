## Configuration file

Trubar can be configured to replace messages with translations (single-language setup) or with lookups into tables of messages (multilingual setup).

Configuration file is a yaml file with options-value pairs, for instance

```
smart-quotes: false
auto-prefix: true
auto-import: "from orangecanvas.localization.si import plsi, plsi_sz"
```

If configuration is not specified, Truber looks for `.trubarconfig.yaml` and `trubar-config.yaml`,respectively, first in the current working directory and then in directory with message file, and then in source directory, as specified by `-s` argument (only for `collect` and `translate`).

The available options are

`smart-quotes` (default: true)
: If set to `false`, strings in translated sources will have the same quotes as in the original source. Otherwise, if translation of a single-quoted includes a single quote, Trubar will output a double-quoted string and vice-versa. If translated message contains both types of quotes, they must be escaped with backslash.

    This setting has not effect in multilingual setup.

`auto-prefix` (default: true)
: If set, Trubar will turn strings into f-strings if translation contains braces and adding an f- prefix makes it a syntactically valid string, *unless* the original string already included braces, in which case this may had been a pattern for `str.format`.

`auto-import` (default: none)
: A string that, if specified, is prepended to the beginning of each source file with translation. The auto-import code is inserted at the top of the file, after any doc strings and imports from the future. The use is described in the section on plural forms.

`static-files` (default: none)
: A path of directory, or a list of paths. whose content is copied into translated sources. See the section on plural forms. This option is overridden by `static` argument in the command line, if given.

`exclude-pattern` (default: `"tests/test_"`)
: A regular expression for filtering out the files that should not be translated. The primary use for this is to exclude unit tests.

`encoding` (default: `"utf-8"`)
: Characted encoding for .jaml files, such as `"utf-8"` or `"cp-1252"`.

### Multilingual setup

In a multilingual setup, the configuration file includes a section with languages. Each language is specified by a key, which is the language code, and a dictionary with options. Options include a name of the language, an international name, and any language-specific auto-import directives. For instance

`name` (required)
: The native name of the language. Put into the table of messages at index 0.

`international-name` (required)
: The international name of the language. Put into the table of messages at index 1.

`auto-import` (default: none)
: Same as `auto-import` in single-language setup, but for the specific language. This text (if any) is added to other auto imports (if any).

`original` (default: false)
: If set to `true`, the language is considered the original language of the source code.

### Example

This is a multilingual setup for two languages that is used in Orange at the time of writing this document.

```yaml
languages:
  en:
    name: English
    original: true
  si:
    name: Slovenščina
    international-name: Slovenian
    auto-import: from orangecanvas.localization.si import plsi, plsi_sz, z_besedo  # pylint: disable=wrong-import-order
auto-import: |2
  from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
  _tr = Translator("Orange", "biolab.si", "Orange")
  del Translator
encoding: "utf-8"
```

For more on auto-imports, see the section on [multilingual use](multilingual.md).
