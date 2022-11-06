## Trubar

A tool for localization of Python messages via translating source files.

Use `trubar -h` for help, or `trubar <action> -h` for help on specific actions.

#### Installation

Trubar is pip-installable:

```sh
pip install trubar`
```

### Trubar works on source level

Unlike gettext, Trubar does not translate by passing a string to a function. Trubar rewrites source files and replaces the original strings with their translations.

Why? For two reasons. Python's f-strings cannot be translated using gettext or similar tools, because they translate a pattern, while f-strings are born interpolated, that is, with expressions already computed.

Furthermore, making the code translatable requires effort by developers and, worse, clutters the code (even calling `_` would add some mess; with `_` having a different meaning a Python, the translation function would have to be called `tr` or similar). We prefer keeping the code clean.

### Translation Workflow

#### Collection - or making a template

We first collect strings in source files into a file. Its extension is arbitrary, but '.yaml' is recommended to help editors help us.

```sh
trubar collect -o translations.yaml
```

`trubar collect` will ignore docstrings and, in general, all strings that appear directly inside modules, classes and functions. These are often used to comment out parts of the code and normally have no effect.


Another start point is to take existing translations into another language and run

```sh
trubar template existing-translations.yaml -o translations.yaml
```

where `existing-translations.yaml` is the name of the file with translations to another language, and `translations.yaml` is the file where you'll put your translations. This is better because the previous translator may have marked the strings that do not require translating. `template` will keep those marks.

We can limit the search to paths that (including the file name) include some pattern, by using `-p pattern`, e.g. `-p widgets/data` or `owtable`. We will however need one big file with all messages, so don't use this option just yet.

#### Filtering out what to translate

Translator can create *translations* by editing this file. Alternatively, (s)he can extract portions of this file into a new file by using `-p` to specify a directory or a file.

```sh
trubar missing translations.yaml -p widgets/data -o data.yaml
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
trubar merge data.yaml translations.yaml
```

This goes through all messages in translation.yaml and adds the translations from data.yaml. Existing translations are not removed if they are not present in the partial translation (with exception of `false` flag, see below). The result is written to translations.yaml.

To write to a different file instead of overwriting the existing translations (better safe than sorry), add the `-o` (`--output`) option.

#### Translating sources

`trubar translate` writes a new tree of source files in which strings are replaced by their translations.

```sh
trubar translate translations.yaml -s sourcepath -d destinationpath
```

If destination already exists it will be overwritten without warning. Any other existing files in destination will not be removed.

#### When source messages change ...

... extract new messages and update them with old translations

```sh
mv translations.yaml old-translations.yaml
trubar collect -o translations.yaml  # or trubar template -o translations-to-another-language.yaml
trubar update old-translations.yaml translations.yaml
```

And keep `old-translations.yaml` for a while, to be safe.


### How to translate

Translations are a stored in hierarchical form. The top-most layer are file paths, which correspond to modules. Below that, there are namespaces, that is, names of classes and functions. These are hierarchical, as they appear in the module. Do not touch those; this is how `trubar translate` knows where to put what. At the bottom-most layer there are pair of messages and translations.

The "translation" can be one of the following:

- a string with translation;
- `null`: the message has not been translated (yet?). This is default, and must be change by translator to one of the below alternatives;
- `false`: the message must not be (or will not) be translated, typically because they are not actually shown to the user but used inside the program, e.g. string literals, names of types, fields in named tuples and similar;
- `true`: the message is a text seen by the user, but needs no translation for this particular language.

The translator's task is to replace `null`'s with `false`'s, `true`'s or translations.

The effect of changing `null` to `false` is that `trubar missing` will treat the message as done, e.g. it will not appear as missing translation. Also, `template` replace translations and falses by nulls, but keeps trues.

#### Quotes

The use of quotes in YAML is optional, unless needed to properly interpret the value. When in doubt, use them. Double quoted strings interpret \n as newline; to have \n in Python source, use \\n. Or single quotes.

The quotes used in YAML are unrelated to quotes used in the corresponding Python code, hence the messages file does not show the type of the quote used in the original source. This could cause problems if translation contains, for instance, a single quote and the Python string itself is enclosed in single quotes. Trubar will detect that and replace the enclosing quotes in translated code, *unless* the translation contains both types of quotes *or* this is explicitly disabled in configuration file.

#### f-strings

The file with translations does not indicate whether the string is an f-string or not. This can be deduced by the presence of `{...}` within the string or checked in the code.

Even if the original is not an f-string, the translation can be an f-string, for instance to add plural forms. Trubar checks whether the translation can be parsed as an f-string and the result contains any expressions, it will add the f-prefix to the string. If in particular project this would lead to false positives, it can be explicitly disabled (but project-wide!) in configuration file.

If the original string is an f-string, the prefix is never removed.

#### Plural forms

Trubar does not care. You can use f-strings, so it's up to you. There is however a neat way of doing it, in particular if the original source already does a part of the job. And Trubar already offers some assistance here.

Suppose there is a module, say `utils.localization` with a function

```python
def pl(n, forms):
    return forms.split("|")[n % 100 != 1]
```

This takes care of plural forms in, for instance English, where one would then use strings like

```python
text += f"<p>{len(table)} {pl(len(table), 'instance|instances')}"
```

In Slovenian translation, we have another function in module `util.localization`:

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

and translate the message to

```python
text += f"<p>{len(table)} {plsi(len(table), 'primer|primer|primeri|primerov')}"
```

Note that this requires importing `plsi` from `utils.localization`. This can be accomplished in two ways. Maybe the original file already imported *all* functions (`from util.localization import *`). If not (for instance because wildcard imports are considered ugly), we can configure Trubar to add `from util.localization import plsi` to all files. See the section about Configuration.

If the original source does not use plural forms but translator would like to use them, (s)he can do so by configuring Trubar to add the necessary import and calling the corresponding function(s). Trubar will turn simple strings to f-strings if necessary. This however needs picking into source code and may break if the code changes. Furthermore, computing the number that is needed to decide the plural form within the f-string itself may be inconvenient.

#### Multiline strings

Do whatever you want. Translate the first line or multiple lines ... it won't change anything.

Future versions of `trubar` may improve in this respect.

### Configuration options

By default, Trubar reads configuration from trubar-config.yaml in the current directory. Another file can be given by `--conf` option.

Configuration file can contain the following options:

- **auto-quotes**: if *true* (default) Trubar will detect single (double) quotes in translations and change the enclosing quotes to double (single), when necessary.
- **auto-prefix**: if *true* (default) Trubar adds the f-prefix if translation looks like an f-string, but the original string was not an f-string
- **auto-import**: a line that is added at the top of each translated file. The intended use is to import the necessary functions for plural forms, e.g. `from utils.localization import plsi, plsi_sz`.
- **encoding**: define a text file encoding different from locale.