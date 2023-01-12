## Questions

##### Why Truebar?

It's not Truebar but Trubar. [Primož Trubar](https://en.wikipedia.org/wiki/Primo%C5%BE_Trubar) was the author of the first printed book in Slovenian language and was also the first to translated parts of the Bible into Slovene.

If it's difficult to remember, imagine that the Tru- part stands for "translation utility", though this is only a coincidence.

##### And Jaml comes from ...?

Shouldn't I, for once, include my name in something? :)

##### Why changing the sources? Why not calling a function, like in gettext?

Because interpolation happens too early for that.

Python's f-strings cannot be translated using gettext or similar tools, because gettexts translates a pattern, while f-strings are born interpolated. For instance, one could translate `"I see {n} little pigs".format(n=7)` because a string `"I see {n} little pigs"` can be passed to `gettext`, which returns a pattern in another language. In case of `f"I see {n} little pigs"`, the string `"I see {n} little pigs"` is never materialized. Syntactically, this is a `JoinedStr`, which is composed of a `Constant` `"I see "`, a `FormattedValue` (essentially `n`) and another `Constant`. At the moment when a `str` object is created and could be passed to `gettext`, the number `n` is already interpolated, hence `gettext` would receive a string like `"I see 7 little pigs"`.

##### Still, why not at least mark strings for translation in sources?

First: why? You can either make it for translation in sources, or mark it for non-translation (`false`) in message files.

Second: unless developpers are dedicated and disciplined, they will fail to mark strings, so somebody will have to mess with source later on.

Third, it clutters the code. In `gettext`, the function that returns a translation is named `_`; this adds an underscore and parentheses (possibly within another parentheses...). In Python, `_` conventionally has a special meaning, so a longer name and more "visible" name would be required. We prefer keeping the code clean.

##### What if the same string appears twice in the same function/class/module, but needs different translations?

Huh, find a neutral translation, or talk to developpers and ask them to split the function into two. Among 15 thousands messages in project Orange, this happenned ones and was resolvable by an (imperfect) neutral translation.