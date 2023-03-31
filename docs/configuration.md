## Configuration file

Configuration file is a yaml file with options-value pairs, for instance

```
smart-quotes: false
auto-prefix: true
auto-import: "from orangecanvas.utils.localization.si import plsi, plsi_sz"
```

If configuration is not specified, Truber looks for `.trubarconfig.yaml` and `trubar-config.yaml`,respectively, first in the current working directory and then in directory with message file, and then in source directory, as specified by `-s` argument (only for `collect` and `translate`).

The available options are

`smart-quotes` (default: true)
: If set to `false`, strings in translated sources will have the same quotes as in the original source. Otherwise, if translation of a single-quoted includes a single quote, Trubar will output a double-quoted string and vice-versa. If translated message contains both types of quotes, they must be escaped with backslash.

`auto-prefix` (default: true)
: If set, Trubar will turn strings into f-strings if translation contains braces and adding an f- prefix makes it a syntactically valid string, *unless* the original string already included braces, in which case this may had been a pattern for `str.format`.

`auto-import` (default: none)
: A string that, if specified, is prepended to the beginning of each source file with translation. The use is described in the section on plural forms.

`static-files` (default: none)
: A path of directory, or a list of paths. whose content is copied into translated sources. See the section on plural forms. This option is overridden by `static` argument in the command line, if given.

`exclude-pattern` (default: `"tests/test_"`)
: A regular expression for filtering out the files that should not be translated. The primary use for this is to exclude unit tests.

`encoding` (default: system locale)
: Characted encoding for .jaml files, such as `"utf-8"` or `"cp-1252"`.
