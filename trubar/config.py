import sys
import os
import re
import locale
import dataclasses

import yaml


@dataclasses.dataclass
class Configuration:
    smart_quotes: bool = True
    auto_prefix: bool = True

    auto_import: str = ""

    static_files: str = ""

    exclude_pattern: str = "tests/test_"

    encoding: str = \
        "locale" if sys.version_info >= (3, 10) \
        else locale.getpreferredencoding(False)

    def __post_init__(self):
        self.__update_exclude_re()

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
                    if value is None:
                        value = field.type()
                    else:
                        value = field.type(value)
                except ValueError:
                    print(f"Invalid value for '{name}': {value}")
                    sys.exit(4)
            setattr(self, name, value)

        self.__update_exclude_re()
        self.__check_static_files()

    def set_static_files(self, static):
        self.static_files = static
        self.__check_static_files()

    def set_exclude_pattern(self, pattern):
        self.exclude_pattern = pattern
        self.__update_exclude_re()

    def __update_exclude_re(self):
        # This function is called from (post)init
        # pylint: disable=attribute-defined-outside-init
        self.exclude_pattern = self.exclude_pattern.strip()
        if self.exclude_pattern:
            self.exclude_re = re.compile(self.exclude_pattern)
        else:
            self.exclude_re = None

    def __check_static_files(self):
        if self.static_files and not os.path.exists(self.static_files):
            print(f"Static files not found in {self.static_files}")
            sys.exit(4)


config = Configuration()
