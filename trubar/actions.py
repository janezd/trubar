import os
import locale
import shutil
import sys
from dataclasses import dataclass
from typing import Union, Iterator, Tuple, Dict, List, Optional

import yaml
import libcst as cst
from libcst.metadata import ParentNodeProvider

__all__ = ["collect", "translate", "merge", "missing", "template",
           "load", "dump"]

MsgDict = Dict[str, Union["MsgDict", str]]
NamespaceNode = Union[cst.Module, cst.FunctionDef, cst.ClassDef]
SomeString = Union[cst.SimpleString, cst.FormattedString]

__encoding = "locale" if sys.version_info >= (3, 10) \
    else locale.getpreferredencoding(False)


def set_encoding(encoding):
    global __encoding  # pylint: disable=global-statement
    __encoding = encoding


@dataclass
class State:
    node: NamespaceNode
    name: str


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
        self.function_stack.append(State(node, name))
        self.contexts.append({})

    def pop_context(self) -> None:
        state = self.function_stack.pop()
        context = self.contexts.pop()
        if context:
            # TODO: somehow decorate the name - function name can be the same as
            # a string!
            self.contexts[-1][state.name or state.node.name.value] = context

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
            self.contexts[-1][text] = None
        return False  # don't visit anything within an f-string!

    def visit_SimpleString(self, node: cst.SimpleString) -> bool:
        lq = len(node.quote)
        s = self.module.code_for_node(node)[len(node.prefix) + lq:-lq]
        if s and not self.is_useless_string(node):
            self.contexts[-1][s] = None
        return False  # doesn't matter, there's nothing down there anyway


class StringTranslator(cst.CSTTransformer):
    def __init__(self, context: MsgDict, module: cst.Module):
        super().__init__()
        self.module = module
        self.context_stack: List[MsgDict] = [context]

    @property
    def context(self):
        return self.context_stack[-1]

    def push_context(self, node: NamespaceNode) -> None:
        self.context_stack.append(self.context.get(node.name.value, {}))

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
        translation = self.context.get(original)
        if not isinstance(translation, str):
            return updated_node
        return cst.parse_expression(
            f'{node.prefix}{node.quote}{translation}{node.quote}')

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


def walk_files(path: str, pattern: str = "", *, skip_nonpython: bool
               ) -> Iterator[Tuple[str, str]]:
    for dirpath, _, files in sorted(os.walk(path)):
        for name in sorted(files):
            if skip_nonpython and (name.startswith("test_")
                                   or not name.endswith(".py")):
                continue
            name = os.path.join(dirpath, name)
            if pattern in name:
                yield name[len(path) + 1:], name


def collect(source: str, pattern: str, *, quiet=False) -> MsgDict:
    collector = StringCollector()
    for name, fullname in walk_files(source, pattern, skip_nonpython=True):
        if not quiet:
            print(f"Parsing {name}")
        with open(fullname, encoding=__encoding) as f:
            tree = cst.metadata.MetadataWrapper(cst.parse_module(f.read()))
            collector.open_module(name)
            tree.visit(collector)
    return collector.contexts[0]


def translate(translations: MsgDict,
              source: Optional[str],
              destination: Optional[str],
              pattern: str,
              *, quiet=False, dry_run=False) -> None:
    source = source or "."
    destination = destination or "."
    for name, fullname in walk_files(source, pattern, skip_nonpython=False):
        transname = os.path.join(destination, name)
        path, _ = os.path.split(transname)
        if not dry_run:
            os.makedirs(path, exist_ok=True)
        if not name.endswith(".py"):
            if not dry_run:
                shutil.copyfile(fullname, transname)
            continue

        with open(fullname, encoding=__encoding) as f:
            orig_source = f.read()
            tree = cst.parse_module(orig_source)
        translator = StringTranslator(translations[name], tree)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        if not quiet:
            print(f"Writing {name}")
        if not dry_run:
            with open(transname, "wt", encoding=__encoding) as f:
                f.write(trans_source)


def missing(translations: MsgDict,
            messages: MsgDict,
            pattern: str = "") -> MsgDict:
    no_translations = {}
    for obj, orig in messages.items():
        if pattern not in obj:
            continue
        trans = translations.get(obj)
        if trans is None or (isinstance(trans, dict) != isinstance(orig, dict)):
            no_translations[obj] = orig  # orig may be `None` or a whole subdict
        elif isinstance(orig, dict):
            if submiss := missing(translations[obj], orig, ""):
                no_translations[obj] = submiss
    return no_translations


def merge(additional: MsgDict, existing: MsgDict, pattern: str = "",
          path: str = "") -> MsgDict:

    def skip(s):
        print(f"{npath}: {s}; rejected")
        rejected[msg] = trans

    rejected = {}
    for msg, trans in additional.items():
        if pattern not in msg:
            continue
        npath = path + "/" * bool(path) + msg
        if msg not in existing:
            skip("not in target structure")
        elif isinstance(trans, dict):
            if isinstance(existing[msg], dict):
                subreject = merge(trans, existing[msg], "", npath)
                if subreject:
                    rejected[msg] = subreject
            else:
                skip("target is message, source gives namespace")
        else:
            if not isinstance(existing[msg], dict):
                if trans is not None:
                    existing[msg] = trans
            else:
                skip("targe is namespace, source gives a message")
    return rejected


def template(existing: MsgDict, pattern: str = "") -> MsgDict:
    new_template = {}
    for msg, trans in existing.items():
        if pattern not in msg:
            continue
        if isinstance(trans, dict):
            if subtemplate := template(existing[msg]):
                new_template[msg] = subtemplate
        elif trans is not False:
            new_template[msg] = None
    return new_template


def load(filename: str) -> MsgDict:
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        sys.exit(2)
    try:
        with open(filename, encoding=__encoding) as f:
            return yaml.load(f, Loader=yaml.Loader)
    except yaml.YAMLError as exc:
        print(f"Error while reading file: {exc}")
        sys.exit(3)


def dump(messages: MsgDict, filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(yaml.dump(messages, indent=4, sort_keys=False,
                          encoding="utf-8", allow_unicode=True))
