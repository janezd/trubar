import os
import sys
from dataclasses import dataclass
from typing import Union, Iterator, Tuple, Dict, List, Optional

import yaml
import libcst as cst
from libcst.metadata import ParentNodeProvider

__all__ = ["collect", "translate", "update", "missing", "load", "dump",
           "set_root_dir", "any_translations"]

root_dir = ""

MsgDict = Dict[str, Union["MsgDict", str]]
NamespaceNode = Union[cst.Module, cst.FunctionDef, cst.ClassDef]


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
        self.function_stack: List[State] = []
        self.contexts: List[MsgDict] = [{}]

    def open_module(self, name: str) -> None:
        self.module_name = name

    def visit_Module(self, node: cst.Module) -> None:
        self.module = node
        self.push_context(node, self.module_name)

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

    def blacklisted(self, node: cst.CSTNode) -> bool:
        ssl = self.get_metadata(ParentNodeProvider, node)
        return (isinstance(ssl, cst.SimpleStatementLine)
                and len(ssl.body) == 1
                and self.get_metadata(ParentNodeProvider, ssl)
                is self.function_stack[-1])

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.push_context(node)

    def leave_ClassDef(self, _) -> None:
        self.pop_context()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.push_context(node)

    def leave_FunctionDef(self, _) -> None:
        self.pop_context()

    def visit_FormattedString(
            self,
            node: cst.FormattedStringExpression) -> None:
        if not self.blacklisted(node):
            self.contexts[-1][self.module.code_for_node(node)[2:-1]] = None
        return False

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        s = self.module.code_for_node(node)[1:-1]
        if s and not self.blacklisted(node):
            self.contexts[-1][s] = None


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
            node: cst.CSTNode, updated_node: cst.CSTNode,
            pref: str) -> cst.CSTNode:
        if not self.context:
            return updated_node
        original = self.module.code_for_node(node)[1 + len(pref):-1]
        translation = self.context.get(original)
        if not translation or translation is True:
            return updated_node
        return cst.parse_expression(f'{pref}"{translation}"')

    visit_ClassDef = push_context
    visit_FunctionDef = push_context

    leave_ClassDef = __leave
    leave_FunctionDef = __leave

    def leave_FormattedString(
            self,
            node: cst.FormattedStringExpression,
            updated_node: cst.FormattedStringExpression) -> cst.CSTNode:
        return self.__translate(node, updated_node, "f")

    def leave_SimpleString(
            self,
            node: cst.SimpleString,
            updated_node: cst.SimpleString) -> cst.CSTNode:
        return self.__translate(node, updated_node, "")


def walk_files(pattern: str) -> Iterator[Tuple[str, str, str]]:
    for root, _, files in os.walk(root_dir):
        for name in files:
            fullname = os.path.join(root, name)
            if pattern in fullname \
                    and fullname[-3:] == ".py" \
                    and not name.startswith("test_"):
                yield root, name, fullname


def collect(pattern: str) -> MsgDict:
    collector = StringCollector()
    for *_, fullname in walk_files(pattern):
        print(f"Parsing {fullname}")
        with open(fullname) as f:
            tree = cst.metadata.MetadataWrapper(cst.parse_module(f.read()))
            collector.open_module(fullname)
            tree.visit(collector)
    return collector.contexts[0]


def translate(translations: MsgDict, destination: str, pattern: str) -> None:
    for root, name, fullname in walk_files(pattern):
        if not any_translations(translations.get(fullname, {})):
            continue
        with open(fullname) as f:
            orig_source = f.read()
            tree = cst.parse_module(orig_source)
        translator = StringTranslator(translations[fullname], tree)
        translated = tree.visit(translator)
        trans_source = tree.code_for_node(translated)
        if orig_source != trans_source:
            transname = os.path.join(destination, root, name)
            print(f"Writing {transname}")
            with open(transname, "wt") as f:
                f.write(trans_source)


def missing(translations: MsgDict, messages: MsgDict, pattern: str) -> MsgDict:
    no_translations = {}
    for obj, orig in messages.items():
        if pattern not in obj:
            continue
        trans = translations.get(obj)
        if trans is None or (isinstance(trans, dict) != isinstance(orig, dict)):
            no_translations[obj] = orig
        elif isinstance(orig, dict):
            if submiss := missing(translations[obj], orig, ""):
                no_translations[obj] = submiss
    return no_translations


def update(existing: MsgDict, additional: MsgDict, pattern: str) -> MsgDict:
    for msg, trans in additional.items():
        if pattern not in msg:
            continue
        if isinstance(trans, dict):
            update(existing.setdefault(msg, {}), trans, "")
        elif trans is not None:
            existing[msg] = trans
    return existing


def load(filename: str) -> MsgDict:
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        sys.exit(2)
    try:
        return yaml.load(open(filename), Loader=yaml.Loader
        )
    except yaml.YAMLError as exc:
        print(f"Error while reading file: {exc}")
        sys.exit(3)


def dump(messages: MsgDict, filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(yaml.dump(messages, indent=4, sort_keys=False,
                          encoding="utf-8", allow_unicode=True))


def any_translations(context):
    return any(any_translations(obj) if isinstance(obj, dict) else obj
               for obj in context.values())


def set_root_dir(dir: str):
    global root_dir
    root_dir = dir
