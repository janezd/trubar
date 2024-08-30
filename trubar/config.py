import sys
import os
import re
import locale
import dataclasses
from typing import Optional

import yaml


@dataclasses.dataclass
class LanguageDef:
    name: str
    international_name: str
    is_original: bool

@dataclasses.dataclass
class Configuration:
    base_dir: Optional[str] = None
    smart_quotes: bool = True
    auto_prefix: bool = True

    auto_import: tuple = ()

    static_files: tuple = ()

    exclude_pattern: str = "tests/test_"

    encoding: str = "utf-8"

    languages = None

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

        self.base_dir, _ = os.path.split(filename)
        fieldict = {field.name: field for field in dataclasses.fields(self)}
        for name, value in settings.items():
            if name == "languages":
                self.parse_languages(value)
                continue
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
                    elif field.type is tuple and isinstance(value, str):
                        value = (value, )
                    else:
                        value = field.type(value)
                except ValueError:
                    print(f"Invalid value for '{name}': {value}")
                    sys.exit(4)
            if field.type is tuple and hasattr(self, name):
                setattr(self, name, getattr(self, name) + value)
            else:
                setattr(self, name, value)

        self.__update_exclude_re()
        if isinstance(self.static_files, str):
            self.static_files = (self.static_files, )
        self.__check_static_files()

    def parse_languages(self, value):
        language_options = {"name", "original", "international-name",
                            "auto-import"}
        self.languages = {}
        for code, values in value.items():
            if "name" not in values:
                print(f"Language '{code}' is missing a 'name' option")
                sys.exit(4)
            name = values["name"]
            international_name = values.get("international-name", name)
            # Use a list, not set to keep the original order
            unknown = [opt for opt in values if opt not in language_options]
            if unknown:
                print(f"Unknown options for language '{code}': " +
                      ', '.join(unknown))
                sys.exit(4)
            is_original = values.get("original", False)
            lang_dir = os.path.join(self.base_dir, code)
            if not (is_original or os.path.exists(lang_dir)):
                print(f"Directory for language '{code}' is missing "
                      f"({lang_dir}).")
                sys.exit(4)
            self.languages[code] = LanguageDef(
                name=name,
                international_name=international_name,
                is_original=is_original
            )
            if "auto-import" in values:
                self.auto_import = self.auto_import + (values["auto-import"], )
            static_dir = os.path.join(lang_dir, "static")
            if os.path.exists(static_dir):
                self.static_files = self.static_files + (static_dir, )
        sorted_langs = sorted(self.languages.items(),
                              key=lambda item: not item[1].is_original)
        if not sorted_langs[0][1].is_original:
            print("Original language is not defined")
            sys.exit(4)
        self.languages = dict(sorted_langs)

    def set_static_files(self, static):
        self.static_files = self.static_files + tuple(static)
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
        for path in self.static_files:
            if not os.path.exists(path):
                print(f"Static files path '{path}' does not exist")
                sys.exit(4)


config = Configuration()
