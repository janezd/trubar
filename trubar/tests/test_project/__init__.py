"""Doc string"""

import os

class A:
    '''Doc string'''

    a = "A class attribute"

    def f(self, x="default"):
        "Doc string"

        t = os.listdir("some/directory")
        for x in t:
            print(f"File {x}")
            print(f'Not file {x + ".bak"}')
            if x.endswith(f"""{"nonsense"}"""):
                return x

if __name__ == "__main__":
    print("Please don't run this.")
    print('Import it, if you must.')