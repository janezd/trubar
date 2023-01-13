## F-strings and localization issues

F-strings offer a powerful support for translation into language with complex grammar.

### Automated f-strings

Trubar sometimes turn strings into f-string in translated files.

If the original source contains an f-string, Trubar will keep the f-prefix in translated source even if the translation does not contain any parts to interpolate. Superfluous f-prefixes do not hurt.

If the original string is not an f-string but the translation contains braces and prefixing this string with f- makes it a syntactically valid f-string, Trubar will add an f-prefix unless:

- the original string already included braces (so this may be a pattern for `str.format`)
- or this behaviour is explicitly disabled in [configuration](../configuration) by setting `auto-prefix: false`.


### Plural forms

Trubar does not itself offer any specific functionality for plural forms. There is however a neat way of doing it, in particular if the original source is written in a translation-friendly way.

The number of pigs in the getting started example is between 5 and 20, which requires a plural in any language with which the author of this text is sufficiently familiar. But now suppose that the number of pigs can be an arbitrary non-negative number. How do we translate `"{self.n} little pigs went for a walk"`?

#### Plural forms in English

The simplest way to support English plural in a large project would be to have a module, say in file `utils.localization.__init__.py`, with a function

```python
def pl(n: int, forms: str) -> str:
    plural = int(n != 1)

    if "|" in forms:
        return forms.split("|")[plural]

    if forms[-1] in "yY" and forms[-2] not in "aeiouAEIOU":
        word = [forms, forms[:-1] + "ies"][plural]
    else:
        word = forms + "s" * plural
    if forms.isupper():
        word = word.upper()
    return word
```

With this, the above string should be written as

```python
"{self.n} little {pl(self.n, 'pig')} went for a walk"
```

The function take care of regular-ish plural forms, including `"piggy"` (`"piggies"`) as well as `"monkey"` (`"monkeys"`). If the plural is irregular, it requires both forms, separated by `|`, e.g. `pl(n, "leaf|leaves")`.

#### Plural forms for other languages

For other languages, one can write a similar module. If the project already includes `utils/localization/__init__.py`, an appropriate place for a Slovenian-language functions would be `utils/localization/si.py`.

The function can be arbitrarily complex. This one takes care of Slovenian nouns, which have four plural forms in nominative and three in other cases, and also offers some automation for nominative case of some regular nouns.

```python
def plsi(n: int, forms: str) -> str:
    n = abs(n) % 100
    if n == 4:
        n = 3
    elif n == 0 or n >= 5:
        n = 4
    n -= 1

    if "|" in forms:
        forms = forms.split("|")
        if n == 3 and len(forms) == 3:
            n -= 1
        return forms[n]

    if forms[-1] == "a":
        return forms[:-1] + ("a", "i", "e", "")[n]
    else:
        return forms + ("", "a", "i", "ov")[n]
```

The translation of 

```python
{self.n} {pl(self.n, 'pig')}
```

into Slovenian is then

```python
{self.n} {plsi(self.n, 'pujsek|pujska|pujski|pujskov')}
```

while the entire sentence

```python
{self.n} little pigs went for a walk
```

requires changing most of the sentence

```python
`"{self.n} {plsi(self.n, 'pujsek se je šel|pujska sta se šla|pujski so se šli|pujskov se je šlo')} sprehajat."`
```

Note that this works even if the original message does not contain any plural forms, for instance because the way it is phrased original is independent of the number. The only condition is that the number, in our case `self.n` is easily accessible in the string.

This is also the reason why Trubar automatically turns strings into f-strings when it detects braces with expressions.

#### Other localization functions

The language-specific module can contain other support functions. For instance, the Slovenian translation of the word "with" in a message `"With {self.n} {pl(self.n, 'pigs')}"` is either "s" or "z", depending on the first sound of the number. Therefore, the Slovenian module for localization includes a function `plsi_sz(n)` that returns the necessary preposition for the given. The translation of the above would thus be 

```
{plsi_sz(self.n)} {self.n} {pl(self.n, 'pujskom|pujskoma|pujski')}
```

The same mechanism can be used for other language quirks.

#### Importing localization functions

The above examples requires importing the localization functions, such as `plsi` and `plsi_sz`.

First, the translated sources must include the necessary module, which does not exist in the original source. To this end, we need to prepare a directory with static files. In our case, we can have a directory named, for instance `si-local`, containing `si-local/utils/localization/__init__.py`. When translating, we instruct Trubar to copy this into translated source tree by adding an option `--static si-local` to the [`translate` action](../command-line/#translate).

Second, all translated source files must include the necessary import. We do this using a directive in [configuration file](../configuration):

```
auto-import: "from orangecanvas.utils.localization.si import plsi, plsi_sz"
```

Trubar will prepend this line to the beginning of all files with any translations.

#### Other forms of interpolation

While Trubar works best with f-strings, other forms of interpolation in Python, `%` and `format` can sometimes be translated, provided the required data can be extracted. For instance, with `"%i little pigs" % self.n`, the translator would see the string part, `%i little pigs` and could translate it to `"{plsi(self.n, '%i pujsek|%i pujska|%i pujski|%i pujskov')}"`, that is, (s)he would replace the entire string with variations corresponding to different values of `self.n`.

Persuading developpers to use f-strings is obviously a better alternative.