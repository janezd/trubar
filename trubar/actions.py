import dataclasses
import os
import re
import shutil
from typing import Union, Iterator, Tuple, List, Optional, NamedTuple

import libcst as cst
from libcst.metadata import ParentNodeProvider

from trubar.messages import MsgNode, MsgDict
from trubar.config import config


__all__ = ["collect", "translate", "merge", "missing", "template",
           "ReportCritical", "ReportUpdates", "ReportTranslations", "ReportAll"]


NamespaceNode = Union[cst.Module, cst.FunctionDef, cst.ClassDef]
SomeString = Union[cst.SimpleString, cst.FormattedString]


re_single_quote = re.compile(r"(^|[^\\])'")
re_double_quote = re.compile(r'(^|[^\\])"')
re_braced = re.compile(r"{.+}")


class State(NamedTuple):
    node: NamespaceNode
    name: str


def prefix_for_node(node: NamespaceNode):
    if isinstance(node, cst.FunctionDef):
        return "def "
    elif isinstance(node, cst.ClassDef):
        return "class "
    assert isinstance(node, cst.Module)
    return ""


class StringCollector(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (ParentNodeProvider, )

    def __init__(self):
        super().__init__()
        self.module: Optional[cst.Module] = None
        self.module_name: Optional[str] = None
        # The stack of nodes (module, class, function) corresponding to
        # the element of stack of contexts
        self.function_stack: List[State] = []
        self.contexts: List[MsgDict] = [{}]

    def open_module(self, name: str) -> None:
        self.module_name = name

    def visit_Module(self, node: cst.Module) -> bool:
        self.module = node
        self.push_context(node, self.module_name)
        return True

    def leave_Module(self, _) -> None:
        self.pop_context()

    def push_context(self, node: NamespaceNode, name=None) -> None:
        if name is None:
            name = f"{prefix_for_node(node)}`{node.name.value}`"
        self.function_stack.append(State(node, name))
        self.contexts.append({})

    def pop_context(self) -> None:
        state = self.function_stack.pop()
        context = self.contexts.pop()
        if context:
            self.contexts[-1][state.name] = MsgNode(context)

    def is_useless_string(self, node: cst.CSTNode) -> bool:
        # This is primarily to exclude docstrings: exclude strings if they
        # represent the entire body of a simple statement.
        # It will not exclude, e.g. line `"a" + "b"`.
        parent = self.get_metadata(ParentNodeProvider, node)
        grand = self.get_metadata(ParentNodeProvider, parent)
        return isinstance(parent, cst.Expr) \
            and isinstance(grand, cst.SimpleStatementLine) \
            and len(grand.body) == 1

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self.push_context(node)
        return True

    def leave_ClassDef(self, _) -> None:
        self.pop_context()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self.push_context(node)
        return True

    def leave_FunctionDef(self, _) -> None:
        self.pop_context()

    def visit_FormattedString(
            self,
            node: cst.FormattedString) -> bool:
        lq = len(node.quote)
        if not self.is_useless_string(node):
            text = self.module.code_for_node(node)[len(node.prefix) + lq:-lq]
            self.contexts[-1][text] = MsgNode(None)
        return False  # don't visit anything within an f-string!

    def visit_SimpleString(self, node: cst.SimpleString) -> bool:
        lq = len(node.quote)
        s = self.module.code_for_node(node)[len(node.prefix) + lq:-lq]
        if s and not self.is_useless_string(node):
            self.contexts[-1][s] = MsgNode(None)
        return False  # doesn't matter, there's nothing down there anyway


class TranslationError(Exception):
    pass


class StringTranslator(cst.CSTTransformer):
    def __init__(self, context: MsgDict, module: cst.Module):
        super().__init__()
        self.module = module
        self.context_stack: List[MsgDict] = [context]

    @property
    def context(self):
        return self.context_stack[-1]

    def _error_context(self):
        return ":".join(
            [name for name, sub in prev.items() if sub is cont][0]
            for prev, cont in zip(self.context_stack, self.context_stack[1:]))

    def push_context(self, node: NamespaceNode) -> None:
        key = f"{prefix_for_node(node)}`{node.name.value}`"
        space = self.context[key].value if key in self.context else {}
        self.context_stack.append(space)

    def pop_context(self) -> None:
        self.context_stack.pop()

    def __leave(self, _, updated_node: cst.CSTNode) -> cst.CSTNode:
        self.pop_context()
        return updated_node

    def __translate(
            self,
            node: SomeString, updated_node: SomeString) -> cst.CSTNode:
        if not self.context:
            return updated_node
        lq = len(node.quote)
        original = self.module.code_for_node(node)[len(node.prefix) + lq:-lq]
        if original not in self.context:
            return updated_node
        translation = self.context[original].value
        if translation in (None, False, True):
            return updated_node
        assert isinstance(translation, str)

        quote = node.quote
        if config.smart_quotes:
            has_single = re_single_quote.search(translation)
            has_double = re_double_quote.search(translation)
            if quote == "'" and has_single and not has_double:
                quote = '"'
            elif quote == '"' and has_double and not has_single:
                quote = "'"

        if config.auto_prefix \
                and "f" not in node.prefix and not re_braced.search(original) \
                and re_braced.search(translation) :
            try:
                new_node = cst.parse_expression(
                    f'f{node.prefix}{quote}{translation}{quote}')
            except cst.ParserSyntaxError:
                pass
            else:
                assert isinstance(new_node, cst.FormattedString)
                if any(isinstance(part, cst.FormattedStringExpression)
                       for part in new_node.parts):
                    return new_node

        try:
            return cst.parse_expression(f'{node.prefix}{quote}{translation}{quote}')
        except cst.ParserSyntaxError:
            if "\n" in translation and len(quote) != 3:
                unescaped = " Unescaped \\n?"
            else:
                unescaped = ""
            raise TranslationError(
                f'\nProbable syntax error in translation.{unescaped}\n'
                f'Original: {original}\n'
                f'Translation: {translation}') from None

    visit_ClassDef = push_context
    visit_FunctionDef = push_context

    leave_ClassDef = __leave
    leave_FunctionDef = __leave

    def leave_FormattedString(
            self,
            original_node: cst.FormattedString,
            updated_node: cst.FormattedString) -> cst.CSTNode:
        return self.__translate(original_node, updated_node)

    def leave_SimpleString(
            self,
            original_node: cst.SimpleString,
            updated_node: cst.SimpleString) -> cst.CSTNode:
        return self.__translate(original_node, updated_node)


def walk_files(path: str, pattern: str = "", *, select: bool
               ) -> Iterator[Tuple[str, str]]:
    path = os.path.normpath(path)
    for dirpath, _, files in sorted(os.walk(path)):
        for name in sorted(files):
            if select and not name.endswith(".py"):
                continue
            name = os.path.join(dirpath, name)
            keyname = name[len(path) + 1:]
            if pattern in name and \
                    not (select and config.exclude_re
                         and config.exclude_re.search(keyname)):
                yield keyname, name


def collect(source: str, pattern: str, *, quiet=False) -> MsgDict:
    collector = StringCollector()
    for name, fullname in walk_files(source, pattern, select=True):
        if not quiet:
            print(f"Parsing {name}")
        with open(fullname, encoding=config.encoding) as f:
            tree = cst.metadata.MetadataWrapper(cst.parse_module(f.read()))
            collector.open_module(name)
            tree.visit(collector)
    return collector.contexts[0]


ReportCritical, ReportUpdates, ReportTranslations, ReportAll = range(4)


def translate(translations: MsgDict,
              source: Optional[str],
              destination: Optional[str],
              pattern: str,
              *, verbosity=ReportUpdates, dry_run=False) -> None:
    def write_if_different(data, dest):
        try:
            with open(dest, encoding=config.encoding) as f:
                diff = 1 if f.read() != data else 0
        except OSError:
            diff = 2
        if diff and not dry_run:
            with open(dest, "wt", encoding=config.encoding) as f:
                f.write(data)
        return diff

    def copy_if_different(src, dest):
        with open(src, encoding=config.encoding) as f:
            return write_if_different(f.read(), dest)

    if dry_run:
        def noop(*_, **_1):
            pass

        copyfile = copytree = makedirs = noop

    else:
        copyfile, copytree = shutil.copyfile, shutil.copytree
        makedirs = os.makedirs

    any_reports = False

    def report(s, level):
        nonlocal any_reports
        if level <= verbosity:
            any_reports = True
            print(s)

    source = source or "."
    destination = destination or "."
    for name, fullname in walk_files(source, pattern, select=False):
        transname = os.path.join(destination, name)
        path, _ = os.path.split(transname)
        makedirs(path, exist_ok=True)

        # Copy anything that is not Python
        if not name.endswith(".py") \
                or config.exclude_re and config.exclude_re.search(fullname):
            copyfile(fullname, transname)
            continue

        # Copy files without translations
        if name not in translations or \
                not _any_translations(translations[name].value):
            diff = copy_if_different(fullname, transname)
            if diff:
                report(f"Copying {name} (no translations)", ReportAll)
            else:
                report(f"Skipping {name} (unchanged; no translations)",
                       ReportAll)
            continue

        # Parse original sources
        try:
            with open(fullname, encoding=config.encoding) as f:
                orig_source = f.read()
                tree = cst.parse_module(orig_source)
        except Exception:
            print(f"Error when parsing {name}")
            raise

        # Replace with translations, produce new sources
        try:
            translator = StringTranslator(translations[name].value, tree)
            translated = tree.visit(translator)
            trans_source = tree.code_for_node(translated)
        except Exception:
            print(f"Error when inserting translations into {name}")
            raise
        if config.auto_import:
            trans_source = config.auto_import + "\n\n" + trans_source

        diff = write_if_different(trans_source, transname)
        if diff == 0:
            report(f"Skipping {name} (unchanged)", ReportTranslations)
        elif diff == 1:
            report(f"Updating translated {name}", ReportUpdates)
        else:  # diff == 2
            report(f"Creating translated {name}", ReportUpdates)
    if not dry_run and config.static_files:
        report(f"Copying files from '{config.static_files}'", ReportAll)
        copytree(config.static_files, destination, dirs_exist_ok=True)

    if not any_reports and verbosity > ReportCritical:
        print("No changes.")


def _any_translations(translations: MsgDict):
    return any(isinstance(value, str)
               or isinstance(value, dict) and _any_translations(value)
               for value in (msg.value for msg in translations.values()))


def missing(translations: MsgDict,
            messages: MsgDict,
            pattern: str = "") -> MsgDict:
    no_translations: MsgDict = {}
    for obj, orig in messages.items():
        if pattern not in obj:
            continue
        trans = translations.get(obj)
        if trans is None:
            no_translations[obj] = orig  # orig may be `None` or a whole subdict
        elif isinstance(orig.value, dict):
            if submiss := missing(translations[obj].value, orig.value, ""):
                no_translations[obj] = MsgNode(submiss,
                                               trans.comments or orig.comments)
        elif trans.value is None:
            no_translations[obj] = trans  # this keeps comments
    return no_translations


def merge(additional: MsgDict, existing: MsgDict, pattern: str = "",
          path: str = "", print_unused=True) -> MsgDict:
    unused: MsgDict = {}
    for msg, trans in additional.items():
        if pattern not in msg:
            continue
        npath = path + "/" * bool(path) + msg
        if msg not in existing:
            if trans.value and (not isinstance(trans.value, dict)
                                or _any_translations(trans.value)):
                if print_unused:
                    print(f"{npath} not in target structure")
                unused[msg] = trans
        elif isinstance(trans.value, dict):
            subreject = merge(trans.value, existing[msg].value, "", npath,
                              print_unused=print_unused)
            if subreject:
                unused[msg] = MsgNode(subreject)
        elif trans.value is not None:
            existing[msg] = trans
    return unused


def template(existing: MsgDict, pattern: str = "") -> MsgDict:
    new_template: MsgDict = {}
    for msg, trans in existing.items():
        if pattern not in msg:
            continue
        if isinstance(trans.value, dict):
            if subtemplate := template(trans.value):
                new_template[msg] = MsgNode(subtemplate, trans.comments)
        elif trans.value is not False:
            new_template[msg] = MsgNode(None, trans.comments)
    return new_template


@dataclasses.dataclass
class Stat:
    translated: int = 0
    kept: int = 0
    untranslated: int = 0
    programmatic: int = 0

    def __add__(self, other):
        return Stat(self.translated + other.translated,
                    self.kept + other.kept,
                    self.untranslated + other.untranslated,
                    self.programmatic + other.programmatic)

    def __abs__(self):
        return self.translated + self.kept \
               + self.untranslated + self.programmatic

    @classmethod
    def collect_stat(cls, messages):
        values = [obj.value for obj in messages.values()]
        return sum((cls.collect_stat(value)
                    for value in values if isinstance(value, dict)),
                   start=Stat(sum(isinstance(val, str) for val in values),
                              values.count(True),
                              values.count(None),
                              values.count(False)))


def stat(messages: MsgDict, pattern: str):
    if pattern:
        messages = {k: v for k, v in messages.items() if pattern in k}
    stats = Stat.collect_stat(messages)
    n_all = abs(stats)
    if not n_all:
        print("No messages")
    else:
        print(f"Total messages: {abs(stats)}")
        print()
        print(f"{'Translated:':16}"
              f"{stats.translated:6}{100 * stats.translated / n_all:8.1f}%")
        print(f"{'Kept unchanged:':16}"
              f"{stats.kept:6}{100 * stats.kept / n_all:8.1f}%")
        print(f"{'Programmatic:':16}"
              f"{stats.programmatic:6}{100 * stats.programmatic / n_all:8.1f}%")
        print(f"{'Total completed:':16}"
              f"{n_all - stats.untranslated:6}"
              f"{100 - 100 * stats.untranslated / n_all:8.1f}%")
        print()
        print(f"{'Untranslated:':16}"
              f"{stats.untranslated:6}{100 * stats.untranslated / n_all:8.1f}%")
