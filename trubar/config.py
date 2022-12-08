import sys
import os
import locale
import dataclasses

import yaml


@dataclasses.dataclass
class Configuration:
    auto_quotes: bool = True
    auto_prefix: bool = True

    auto_import: str = ""

    static_files: str = ""

    encoding: str = \
        "locale" if sys.version_info >= (3, 10) \
        else locale.getpreferredencoding(False)

    def update_from_file(self, filename):
        if not os.path.exists(filename):
            print(f"Can't open configuration file {filename}")
            sys.exit(4)
        try:
            with open(filename, encoding=self.encoding) as f:
                settings = yaml.load(f, Loader=yaml.Loader)
        except yaml.YAMLError as exc:
            print(f"Invalid configuration file: {exc}")
            sys.exit(4)

        fieldict = {field.name: field for field in dataclasses.fields(self)}
        for name, value in settings.items():
            name = name.replace("-", "_")
            field = fieldict.get(name, None)
            if field is None:
                print(f"Unrecognized configuration setting: {name}")
                sys.exit(4)
            if field.type is bool and value not in (True, False):
                print(f"Invalid value for '{name}': {value}")
                sys.exit(4)
            else:
                try:
                    value = field.type(value)
                except ValueError:
                    print(f"Invalid value for '{name}': {value}")
                    sys.exit(4)
            setattr(self, name, value)

        self.__check_static_files()

    def set_static_files(self, static):
        self.static_files = static
        self.__check_static_files()

    def __check_static_files(self):
        if self.static_files and not os.path.exists(self.static_files):
            print(f"Static files not found in {self.static_files}")
            sys.exit(4)


config = Configuration()