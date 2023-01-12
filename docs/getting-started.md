## Getting Started 

Imagine a Python project named `sample` with the following typical structure.

```
sample
    farm
        __init__.py
	pigs.py
    __main__.py
setup.py
README
LICENSE
```

File `sample/farm/pigs.py` contains

```python
class PigManager:
    def __init__(self, n):
        if not 5 <= n <= 20:
            raise ValueError(
                f"Wrong number: number of pigs should be between 5 and 20, not {n}.")
        self.n = n

    def walk(self):
        print(f"{self.n} little pigs went for a walk")
```

and `sample/__main__.py` contains

```python
from farm.pigs import PigManager

def main():
    ns = input("Enter a number between 5 and 20: ")
    try:
        n = int(ns)
    except ValueError:
        print(f"'{n}' is not a number")
    else:
        farm = PigManager(n)
        farm.walk()

if __name__ == "__main__":
    main()
```

and `sample/farm/__init__.py` is empty.

Note that, unlike in the gettext framework, messages are not "marked" for translation by being passed through a call to a translation function like `_`, `tr` or `gettext`.

### Collecting messages

To collect all strings in the project, use [collect](/command-line/#collect).

```
trubar collect -s code/sample -o sample.jaml
```

The first argument `-s` gives the root directory. This will usually not be the root of the project, which only contains "administrative" files like setup.py, but the directory with actual sources that need translation.

The found strings are written into the output file, in our example `sample.jaml`.

```raw
__main__.py:
    def `main`:
        'Enter a number between 5 and 20: ': null
        "'{n}' is not a number.": null
    __main__: null
farm/pigs.py:
    class `PigManager`:
        def `__init__`:
            'Wrong number: number of pigs should be between 5 and 20, not {n}.': null
        def `walk`:
            {self.n} little pigs went for a walk: null
```

See the section about [Message files](/message-files) for details about the file format.

### Translating messages

The next step is to edit the .jaml file: `null`'s need to be replaced by translations or marked in another way. Here's a Slovenian translation.

```
__main__.py:
    def `main`:
        'Enter a number between 5 and 20: ': 'Vnesite število med 5 in 20: '
        "'{n}' is not a number.": '{n}' ni število.
    __main__: false
farm/pigs.py:
    class `PigManager`:
        def `__init__`:
            # I translated this, but I'm not sure it's needed.
            'Wrong number: {n} is not between 5 and 20.': Napačno število: {n} ni med 5 in 20.
        def `walk`:
            {self.n} little pigs went for a walk: {self.n} prašičkov se je šlo sprehajat.
```

We translated `__main__` as `false`, which indicates that this string must not be translated. Other options are explained [later](/message-files/#translations).

### Applying translations

In most scenarios, we first need to prepare a copy of the entire project, because Trubar will only copy the files within its scan range. Suppose that `../project_copy` contains such a copy.

Now run [translate](/command-line/#translate).

```
trubar translate -s code/sample -d ../project_copy/code/sample sample.jaml
```

That's it.