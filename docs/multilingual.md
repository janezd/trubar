## Setup for multilingual use

Implementing a multilingual setup requires understanding of the code produced by Trubar.

In single-language setup, strings are replaced by translated strings and f-strings pose no problem. Multilingual setup uses string tables for different languages. F-strings cannot be stored in such tables because they are syntactic elements and not Python objects. Instead, Trubar stores a string that contains an f-string. When the string needs to be used, it compiles and evaluates it in the local context.

### A slightly simplified example

The following example is based on the Orange code base. A similar setup would be used in other projects.

We first need to understand how Trubar modifies the sources in multilingual mode.

- A string `"Data Table"` is replaced by `_tr.m[1651]`. Neither the original string nor any of its translations are f-strings, so the string is replaced by lookup; the element at index 1651 in the English message table is `"Data Table"` and in the Slovenian table it is `"Tabela s podatki"`. We will tell more about where the `_tr` comes from and what it contains later.
- A string `f" ({perc:.1f} % missing data)"))` is replaced by `_tr.e(_tr.c(1717)`. The string at index 1717 in the English message table is `"f\" ({perc:.1f} % missing data)\""` and the Slovenian translation is `"f\" ({perc:.1f} % manjkajočih podatkov)\""`. Note that this is not a string but a string that contains and f-string.

For this to work, the `_tr` must be an object with the following attributes:

- `m` is a list of strings, where the index corresponds to the index in the message table.
- `e` is a function that evaluates a string; in short, `e` is `eval`.
- `c` is a function that compiles a string at the given index; in short, `c` is `compile`.

Trubar provides neither `_tr` nor its methods, and it doesn't import it because this is application specific. Orange's configuration for Trubar has an auto-import directive that inserts the following lines into each source file:

```python
  from orangecanvas.localization import Translator  # pylint: disable=wrong-import-order
  _tr = Translator()
  del Translator
```
Other applications would import a similar class from another location and use different arguments for its constructor. The end result must be an object named `_tr` with the requires methods.

The `Translator` class looks roughly like this:

```python
import json

class Translator:
    def __init__(self):
        path = "i18n/slovenian.jaml"  # Replace this with the actual path
        with open(path) as handle:
            # Note that the actual code is somewhat more complex; see below
            self.m = json.load(handle)

    e = eval

    def c(self, idx, *_):
        return compile(self.m[idx], '<string>', 'eval')
```

In Orange, the `Translator`'s constructor requires Qt-related arguments, so the code from auto-import is actually

```python
_tr = Translator("Orange", "biolab.si", "Orange")
```

and the constructor uses these arguments to retrieve the current language from the settings and locates the appropriate file and reads it into `self.m`.

### The actual code

The above description is simplified for clarity. Trubar doesn't replace `"Data Table"` by `tr.m[1651]` but by `tr.m[1651, "Data Table"]`; similarly for f-strings. The second index, `"Data Table"`, is not used and is there only as a comment for any developers checking the translated sources. Translator doesn't load the message table with

```python
self.m = json.load(handle)
```

but wraps the list into a class `_list`:

```python
self.m = json.load(handle)
```

where `_list` is

```python
class _list(list):
    # Accept extra argument to allow for the original string
    def __getitem__(self, item):
        if isinstance(item, tuple):
            item = item[0]
        return super().__getitem__(item)
```

Note again that Trubar doesn't provide this code, but your application would probably use similar code. Find the complete example at [Orange Canvas Core's Github](https://github.com/biolab/orange-canvas-core/blob/master/orangecanvas/localization/__init__.py).