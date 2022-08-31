## Trubar

A tool for localization of Python messages via translating source files.

Use `trubar -h` for help, or `trubar <action> -h` for help on specific actions.

#### Installation

Trubar is pip-installable:

```sh
pip install trubar`
```

#### Orange-related peculiarities

The tool was developed for Orange. The number of Orange-related things is small (perhaps just a root directory, as described below and which can be changed with an option, and this documentation?) and will be removed in the future if we consider the tool could be useful for other projects as well.

The tool is expected to be run in Orange's root and will look for Python sources in directory Orange/widgets. Another root can be specified by adding option `-r` (`--root`). This "feature" will be removed at some later point.

### Why working on the source level?

Python's f-strings cannot be translated using gettext or similar tools, because they translate a pattern, while f-strings are born interpolated, that is, with expressions already computed.

Furthermore, making the code translatable requires effort by developers and, worse, clutters the code (even calling `_` would add some mess; with `_` having a different meaning a Python, the translation function would have to be called `tr` or similar). We prefer keeping the code clean.

### Translation Workflow

#### Collection

We first collect strings in source files into a file. Its extension is arbitrary, but '.yaml' is recommended to help editors help us.

```sh
trubar collect -o translations.yaml
```

`trubar collect` will ignore docstrings and, in general, all strings that appear directly inside modules, classes and functions. These are often used to comment out parts of the code and normally have no effect.

We can limit the search to paths that (including the file name) include some pattern, by using `-p pattern`, e.g. `-p widgets/data` or `owtable`. We will however need one big file with all messages, so don't use this option just yet.

#### Filtering out what to translate

Translator can create *translations* by editing this file. Alternatively, (s)he can extract portions of this file into a new file using

```sh
trubar missing translations.yaml -p widgets/data -o data.yaml
```

or, for a single widget

```sh
trubar missing translations.yaml -p owtable -o data.yaml
```

(Remember: the pattern is just a part of the path: 'ata/owra' would match data/owrank.py and data/owrandomize.py.)

We then open the smaller file and add translations. More on that in a separate section.

`trubar missing <file>` retrieves the missing translations from that file. If we translated some messages in data.yaml but not all, we can filter it further with

```sh
trubar missing data.yaml -o still-missing.yaml
```

#### Merging translations

We update the "big" translation file with partial translations with

```sh
trubar update data.yaml translations.yaml
```

This goes through all messages in translation.yaml and adds the translations from data.yaml. Existing translations are not removed if they are not present in the partial translation (with exception of `false` flag, see below). The result is written translations.yaml.

If we would like to write to a different file instead of overwriting the existing translations (better safe than sorry), we add the `-o` (`--output`) option.

#### Translating sources

`trubar translate` writes new source files in which strings are replaced by their translations.

For this we need to copy the entire directory with sources. If directories under /somewhere/Orange/widgets are copied to /elsewhere/Orange/widgets,

```sh
trubar translate translations.yaml -s /somewhere -d /elsewhere
```

will write translation to files in /somewhere/Orange/widgets. If destination already exists it will be overwritten without warning.

#### When source messages change ...

... extract new messages and update them with old translations

```sh
mv translations.yaml old-translations.yaml
trubar collect -o translations.yaml
trubar update old-translations.yaml translations.yaml
```

And keep `old-translations.yaml` for a while, to be safe.

#### Being kind to translators

It would be nice to translators if we prepared an empty translation file in which strings that must not be changed are marked by `false` flag (see below). Alternatively, we can another action to `trubar` - updating a file with `false`'s from another file.

### How to translate

Translations are a stored in hierarchical form. The top-most layer are file paths, which correspond to modules. Below that, there are namespaces, that is, names of classes and functions. These are hierarchical, as they appear in the module. Do not touch those; this is how `trubar translate` knows where to put what. At the bottom-most layer there are pair of messages and translations.

The translation can be one of the following:

- `null`: the message has not been translated (yet?). This is default, and must be change by translator to one of the below alternatives.
- `false`: the message must not be (or will not) be translated, typically because they are string literals, names of types, fields in named tuples and similar;
- `true`: the message is a text seen by the user, but needs no translation for this particular language;
- a string with translation.

The translator's task is to replace `null`'s with `false`'s, `true`'s or translations.

The effect of changing `null` to `false` is that `trubar missing` will treat the message as done, e.g. it will not appear as missing translation.

#### Quotes

Messages are shown as strings without quotes. This may cause some problems because it doesn't show the translator which type of quotes is used in the source. It is however preferable to including quotes, because YAML would add quotes to quoted strings and translator would have to do the same.

When in doubt, check the source.

YAML however adds quotes if the messages contains certain characters or ends with semicolon or space. Translator must do the same to conform to YAML format. This doesn't mean that quotes must be present (absent) if they are present (absent) in the original. Quotes can be omitted if unnecessary, and must be added when necessary.

#### f-strings

The file with translations does not (and cannot indicate without a lot of additional clutter) whether the string is an f-string or not. This can be deduced by the presence of `{...}` within the string ... or checked in the code.

Translator cannot replace an ordinary string with an f-string, because (s)he touches only what is between the quotes. If, however, translator decides to exclude data that is interpolated, (s)he may do so by simply omitting the parts between braces; this is still a valid (though pointless) f-string.

#### Plural forms

This is unrelated to `trubar` and can be handled differently in other projects. The way we do it in Orange is as follows.

The source file must import the localization functions, e.g.

```python
from Orange.widgets.utils.localization import *
```

It is crucial to import all functions from the file. The file contains the following function

```python
def pl(n, forms):
    return forms.split("|")[n % 100 != 1]
```

The function is used to formulated plural forms in English messages, as in

```python
text += f"<p>{len(table)} {pl(len(table), 'instance|instances')}"
```

In Slovenian translation, we add another function to that file

```python
def plsi(n, forms):
    forms = forms.split("|")
    if n % 100 == 1:
        return forms[0]
    if n % 100 == 2:
        return forms[1]
    if n % 100 in (3, 4):
        return forms[2]
    return forms[3]
```

We then simply translate the message to

```python
text += f"<p>{len(table)} {plsi(len(table), 'primer|primer|primeri|primerov')}"
```

Replacing the original `pl` function with one that would work for Slovenian plurals would break any untranslated messages. Having the Slovenian function and keeping the original call `pl(len(table), 'instance|instances')` would give index error when `len(table) % 100` is not 1 or 2.

#### Multiline strings

Do whatever you want. Translate the first line or multiple lines ... it won't change anything.

Future versions of `trubar` may improve in this respect.

### Known quirks

Trubar assumes that no string is the same as a function within the same namespace. This would cause problems.

```python
s = "foo"

def foo(x):
    t = "bar"
```
