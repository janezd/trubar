"""Doc string"""
from something import anythin
from anything import something
_tr = Translator("Orange", "biolab.si", "Orange")
del Translator

import os

class A:
    '''Doc string'''

    a = "A class attribute"

    def f(self, x=_tr.e(_tr.c(2, "default"))):
        "Doc string"

        t = os.listdir(_tr.e(_tr.c(3, "some/directory")))
        for x in t:
            print(_tr.e(_tr.c(4, "File {x}")))
            print(_tr.e(_tr.c(5, 'Not file {x + ".bak"}')))
            if x.endswith(_tr.e(_tr.c(6, """{"nonsense"}"""))):
                return x

if __name__ == "__main__":
    print("Please don't run this.")
    print(_tr.e(_tr.c(7, 'Import it, if you must.')))