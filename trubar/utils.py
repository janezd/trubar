import re

import os
import sys
from pathlib import PurePath
from typing import Iterator, Tuple, Optional, Set, List

from trubar.config import config
from trubar.messages import MsgDict, dump


def walk_files(path: str, pattern: str = "", *, select: bool
               ) -> Iterator[Tuple[str, str]]:
    path = os.path.normpath(path)
    for dirpath, _, files in sorted(os.walk(path)):
        for name in sorted(files):
            if name.endswith(".pyc") \
                    or select and not name.endswith(".py"):
                continue
            name = os.path.join(dirpath, name)
            keyname = PurePath(name[len(path) + 1:]).as_posix()
            if pattern in keyname and \
                    not (select and config.exclude_re
                         and config.exclude_re.search(keyname)):
                yield keyname, name


def check_any_files(trans_files: Set[str], path: str):
    source_keys = {n for n, _ in walk_files(path, "", select=True)}
    if not trans_files or source_keys & trans_files:
        return
    suggestion = ""
    best_matched = 2  # Require at least three matches to make a suggestion
    tried = set()
    for fname in source_keys:
        start = ""
        for part in fname.split("/")[:3]:
            start += part + "/"
            if start in tried:
                continue
            tried.add(start)
            matched = len(source_keys & {start + k for k in trans_files})
            if matched > best_matched:
                best_matched = matched
                suggestion = start
    if suggestion:
        suggestion = os.path.join(path, suggestion[:-1])
        if sys.platform != "win32":
            home = os.path.expanduser("~")
            if suggestion.startswith(home):
                suggestion = "~/" + suggestion[len(home) + 1:]
        suggestion = f"; try -s {suggestion} instead"
    print("Paths in translations do not match any existing files.\n"
          f"One reason may be an incorrect source path{suggestion}.")
    sys.exit(5)


def unique_name(name: str) -> str:
    if not os.path.exists(name):
        return name

    path, name = os.path.split(name)
    base, ext = os.path.splitext(name)
    pattern = fr"{re.escape(base)} \((\d+)\){ext}"
    existing = (re.match(pattern, fname) for fname in os.listdir(path or "."))
    ver = 1 + max((int(mo.group(1)) for mo in existing if mo), default=0)
    return os.path.join(path, f"{base} ({ver}){ext}")


def dump_removed(removed: MsgDict,
                 removed_name: Optional[str], name: str) -> None:
    if not removed:
        return
    if not removed_name:
        path, name = os.path.split(name)
        removed_name = os.path.join(path, "removed-from-" + name)
    removed_name = unique_name(removed_name)
    dump(removed, removed_name)


def make_list(s: List[str], verb: Optional[str] = None):
    verb = "" if verb is None else " " + verb + "s" * (len(s) == 1)
    if len(s) == 1:
        return s[0] + verb
    else:
        return ", ".join(s[:-1]) + " and " + s[-1] + verb
