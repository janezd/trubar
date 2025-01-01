import dataclasses
import os
import re
import shutil
import json
from typing import Union, List, Optional, NamedTuple, Tuple, Dict

import libcst as cst
from libcst.metadata import ParentNodeProvider

from trubar.utils import walk_files
from trubar.messages import MsgNode, MsgDict
from trubar.config import config


__all__ = ["collect", "translate", "merge", "missing", "template",
           "ReportCritical", "ReportUpdates", "ReportTranslations", "ReportAll"]


NamespaceNode = Union[cst.Module, cst.FunctionDef, cst.ClassDef]
SomeString = Union[cst.SimpleString, cst.FormattedString]


re_single_quote = re.compile(r"(^|[^\\])'")
re_double_quote = re.compile(r'(^|[^\\])"')
re_braced = re.compile(r"{.+}")
all_quotes = ("'", '"', "'''", '"""')


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

    @classmethod
    def parse_file(cls, fullname: str):
        collector = cls()
        with open(fullname, encoding=config.encoding) as f:
            tree = cst.metadata.MetadataWrapper(cst.parse_module(f.read()))
            tree.visit(collector)
        return MsgNode(collector.contexts[0])

    def __init__(self):
        super().__init__()
        self.module: Optional[cst.Module] = None
        self.module_name: Optional[str] = None
        # The stack of nodes (module, class, function) corresponding to
        # the element of stack of contexts
        self.function_stack: List[State] = []
        self.contexts: List[MsgDict] = []

    def visit_Module(self, node: cst.Module) -> bool:
        self.module = node
        self.push_context(node, "")
        return True

    def push_context(self,
                     node: NamespaceNode,
                     name: Optional[str] = None) -> None:
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


class CountImportsFromFuture(cst.CSTVisitor):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.has_docstring = False

    def visit_Module(self, node: cst.Module):
        self.has_docstring = node.get_docstring()

    def visit_ImportFrom(self, node: cst.ImportFrom):
        if node.module is not None and node.module.value == "__future__":
            self.count += 1
        return False


class StringTranslatorBase(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (ParentNodeProvider, )

    def __init__(self,
                 module: cst.Module,
                 auto_import: Optional[cst.CSTNode] = None,
                 n_future_imports: Optional[int] = 0,
                 has_docstring: bool = False):
        super().__init__()
        self.module = module
        self.context_stack: Union[List[MsgDict], List[List[MsgDict]]] = []
        self.auto_import = auto_import
        self.auto_import_after = n_future_imports or None
        self.import_after_docstring = has_docstring and not n_future_imports

    @property
    def context(self):
        return self.context_stack[-1]

    def push_context(self, node: NamespaceNode) -> None:
        raise NotImplementedError

    def pop_context(self) -> None:
        self.context_stack.pop()

    def __leave(self, _, updated_node: cst.CSTNode) -> cst.CSTNode:
        self.pop_context()
        return updated_node

    def translate(
            self,
            node: SomeString,
            updated_node: SomeString) -> cst.CSTNode:
        raise NotImplementedError

    leave_ClassDef = __leave
    leave_FunctionDef = __leave

    def leave_SimpleStatementLine(self, _, updated_node: cst.CSTNode
                                  ) -> cst.CSTNode:
        # Decrease the counter of __future__imports, and put auto imports
        # after the node when the counter reaches zero
        if self.auto_import is None:
            return updated_node

        if self.auto_import_after is not None:
            self.auto_import_after -= sum(
                isinstance(child, cst.ImportFrom)
                and child.module.value == "__future__"
                for child in updated_node.body)

        if self.import_after_docstring:
            import_now = isinstance(updated_node, cst.SimpleStatementLine)
        else:
            import_now = self.auto_import_after == 0
        if import_now:
            updated_node = cst.FlattenSentinel([updated_node,
                                                *self.auto_import])
            self.auto_import = None
        return updated_node

    def on_leave(self,
                 original_node: cst.CSTNodeT,
                 updated_node: cst.CSTNodeT) -> cst.CSTNode:
        # If there are no imports from __future__ insert auto import
        # before the first node
        updated_node = super().on_leave(original_node, updated_node)
        if self.auto_import \
                and not self.import_after_docstring \
                and self.auto_import_after is None \
                and not isinstance(original_node, cst.Module) \
                and isinstance(
                    self.get_metadata(ParentNodeProvider, original_node),
                    cst.Module):
            updated_node = cst.FlattenSentinel([*self.auto_import,
                                                updated_node])
            self.auto_import = None
        return updated_node

    def visit_ClassDef(self, node: NamespaceNode) -> None:
        self.push_context(node)

    def visit_FunctionDef(self, node: NamespaceNode) -> None:
        self.push_context(node)

    def leave_FormattedString(
            self,
            original_node: cst.FormattedString,
            updated_node: cst.FormattedString) -> cst.CSTNode:
        return self.translate(original_node, updated_node)

    def leave_SimpleString(
            self,
            original_node: cst.SimpleString,
            updated_node: cst.SimpleString) -> cst.CSTNode:
        return self.translate(original_node, updated_node)

    def visit_ConcatenatedString(
            self,
            _) -> bool:
        return False

    def leave_ConcatenatedString(
            self,
            original_node: cst.ConcatenatedString,
            updated_node: cst.ConcatenatedString) -> cst.CSTNode:

        def compose_concatenation(node: cst.ConcatenatedString):
            left = self.translate(node.left, node.left)
            if isinstance(node.right, cst.ConcatenatedString):
                right = compose_concatenation(node.right)
            else:
                right = self.translate(node.right, node.right)
            return cst.BinaryOperation(
                left, cst.Add(), right,
                (cst.LeftParen(),), (cst.RightParen(), ))

        return compose_concatenation(updated_node)


class StringTranslator(StringTranslatorBase):
    def __init__(self,
                 context: MsgDict,
                 module: cst.Module,
                 auto_import: Optional[cst.CSTNode] = None,
                 n_future_imports: Optional[int] = None,
                 has_docstring: bool = False):
        super().__init__(module, auto_import, n_future_imports, has_docstring)
        self.context_stack = [context]

    def push_context(self, node: NamespaceNode) -> None:
        key = f"{prefix_for_node(node)}`{node.name.value}`"
        space = self.context[key].value if key in self.context else {}
        self.context_stack.append(space)

    def translate(
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
            new_node = cst.parse_expression(
                f'{node.prefix}{quote}{translation}{quote}')
        except cst.ParserSyntaxError:
            if "\n" in translation and len(quote) != 3:
                unescaped = " Unescaped \\n?"
            else:
                unescaped = ""
            raise TranslationError(
                f'\nProbable syntax error in translation.{unescaped}\n'
                f'Original: {original}\n'
                f'Translation: {translation}') from None

        return new_node


class StringTranslatorMultilingual(StringTranslatorBase):
    def __init__(self,
                 contexts: List[MsgDict],
                 message_tables: List[List[str]],
                 module: cst.Module,
                 auto_import: Optional[cst.CSTNode] = None,
                 n_future_imports: Optional[int] = None,
                 has_docstring: bool = False):
        super().__init__(module, auto_import, n_future_imports, has_docstring)
        self.context_stack = [contexts]
        self.message_tables = message_tables

    def push_context(self, node: NamespaceNode) -> None:
        key = f"{prefix_for_node(node)}`{node.name.value}`"
        space = [lang_context[key].value if key in lang_context else {}
                 for lang_context in self.context]
        self.context_stack.append(space)

    @classmethod
    def _f_string_languages(cls,
                            prefix: str,
                            original: str,
                            messages: List[str]) -> set[int]:
        """
        For the given messages, return a set of indices of languages that
        requires an f-prefix, excluding the original language.

        This is determined by
         - checking that the string includes braces and, if so,
         - compiling as f-string and checking that the result contains some
           formatted string expressions
        """
        add_f = set()
        if "f" not in prefix:
            prefix += "f"
        for i, translation in enumerate(messages[1:], start=1):
            if re_braced.search(translation):
                try:
                    node = cst.parse_expression(prefix + repr(translation))
                except cst.ParserSyntaxError as exc:
                    languages = list(config.languages.values())
                    language = languages[i].international_name
                    raise TranslationError(
                        f"Probable syntax error in translation to {language}.\n"
                        f"Original: {original}\n"
                        f"Translation:\n  {translation}\n"
                        "This error occurred while trying to compile the "
                        "translation string as an f-string.\n"
                        "The original Python message:"
                    ) from exc

                assert isinstance(node, cst.FormattedString)
                if any(isinstance(part, cst.FormattedStringExpression)
                       for part in node.parts):
                    add_f.add(i)
        return add_f

    def translate(
            self,
            node: SomeString,
            updated_node: SomeString) -> cst.CSTNode:
        if not self.context:
            return updated_node

        lq = len(node.quote)
        orig_str = self.module.code_for_node(node)
        original = orig_str[len(node.prefix) + lq:-lq]

        messages = [lang_context[original].value
                    if original in lang_context else None
                    for lang_context in self.context]
        assert all(isinstance(translation, (str, bool, type(None)))
                   for translation in messages)
        if all(message in (None, False, True) for message in messages):
            return updated_node
        messages = [
            translation if isinstance(translation, str) else original
            for translation in messages]

        idx = len(self.message_tables[0])
        if "f" in node.prefix \
                or config.auto_prefix and not re_braced.search(original):
            need_f = self._f_string_languages(node.prefix, orig_str, messages)
            if "f" in node.prefix:
                need_f.add(0)
        else:
            need_f = set()

        for lang_idx, (message, table) in \
                enumerate(zip(messages, self.message_tables)):
            if "r" not in node.prefix:
                # unescape the translation: we need actual \n, not \ and n
                message = message \
                    .encode('latin-1', 'backslashreplace') \
                    .decode('unicode-escape')
            if need_f:
                # This string will be evaled, "uneval" it through repr
                message = repr(message)
                # Add an f-prefix to the string if needed
                if lang_idx in need_f:
                    message = "f" + message
            table.append(message)

        if need_f:
            trans = f'_tr.e(_tr.c({idx}, {orig_str}))'
        else:
            trans = f"_tr.m[{idx}, {orig_str}]"
        return cst.parse_expression(trans)

def collect(source: str,
            existing: Optional[MsgDict] = None,
            pattern: str = "",
            *, quiet=False, min_time=None) -> Tuple[MsgDict, MsgDict]:
    messages = {}
    removed = {}
    # No pattern when calling walk_files: we must get all files so that
    # existing messages in skipped files are kept. We check the pattern here.
    for name, fullname in walk_files(source, "", select=True):
        if pattern in name and (
                min_time is None or os.stat(fullname).st_mtime >= min_time):
            if not quiet:
                print(f"Parsing {name}")
            collected = StringCollector.parse_file(fullname)
            if collected.value:
                messages[name] = collected
            if name in existing:
                removals = MsgNode(merge(
                    existing.pop(name).value, collected.value,
                    "", name, print_unused=False))
                if removals.value:
                    removed[name] = removals
        elif name in existing:
            messages[name] = existing.pop(name)

    existing = {name: trans for name, trans in existing.items()
                if _any_translations(trans.value)}
    removed.update(existing)
    return messages, removed


ReportCritical, ReportUpdates, ReportTranslations, ReportAll = range(4)


def translate(translations: Dict[str, MsgDict],
              source: str, destination: str, pattern: str,
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

    inplace = os.path.realpath(source) == os.path.realpath(destination)
    if dry_run or inplace:
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

    if config.auto_import:
        imports = cst.parse_module("\n".join(config.auto_import))
        auto_import = imports.body
    else:
        auto_import = None

    if config.languages:
        message_tables = [[language.name, language.international_name]
                          for language in config.languages.values()]
    else:
        message_tables = None

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
        if not any(name in trans and _any_translations(trans[name].value)
                   for trans in translations):
            if inplace:
                continue
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

        if auto_import is not None:
            counter = CountImportsFromFuture()
            tree.visit(counter)
            n_future_imports = counter.count
            has_docstring = counter.has_docstring
        else:
            n_future_imports = None
            has_docstring = None

        # Replace with translations, produce new sources
        try:
            trans_name = [
                trans[name].value if name in trans else {}
                for trans in translations
            ]
            if config.languages is None:
                translator = StringTranslator(
                    trans_name[0],
                    tree,
                    auto_import, n_future_imports, has_docstring)
            else:
                translator = StringTranslatorMultilingual(
                    trans_name, message_tables,
                    tree,
                    auto_import, n_future_imports, has_docstring)
            tree = cst.metadata.MetadataWrapper(tree)
            translated = tree.visit(translator)
            trans_source = tree.module.code_for_node(translated)
        except Exception:
            print(f"Error when inserting translations into {name}")
            raise

        diff = write_if_different(trans_source, transname)
        if diff == 0:
            report(f"Skipping {name} (unchanged)", ReportTranslations)
        elif diff == 1:
            report(f"Updating translated {name}", ReportUpdates)
        else:  # diff == 2
            report(f"Creating translated {name}", ReportUpdates)
    if not dry_run:
        for path in config.static_files:
            report(f"Copying files from '{path}'", ReportAll)
            copytree(path, destination, dirs_exist_ok=True)

    if not any_reports and verbosity > ReportCritical:
        print("No changes.")

    if config.languages:
        i18ndir = os.path.join(destination, "i18n")
        os.makedirs(i18ndir, exist_ok=True)
        for langdef, messages in zip(config.languages.values(), message_tables):
            fname = os.path.join(i18ndir, f"{langdef.international_name}.json")
            with open(fname, "wt", encoding=config.encoding) as f:
                json.dump(messages, f)

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
