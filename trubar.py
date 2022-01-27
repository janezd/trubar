import os
import sys
import warnings
import argparse
from dataclasses import dataclass
from typing import Union, Iterator, Tuple, Dict, List, Optional

import yaml
import libcst as cst


warnings.simplefilter("ignore", yaml.YAMLLoadWarning)
root_dir = ""

MsgDict = Dict[str, Union["MsgDict", str]]
NamespaceNode = Union[cst.Module, cst.FunctionDef, cst.ClassDef]


@dataclass
class State:
    node: NamespaceNode
    blacklist: List[cst.CSTNode]
    name: str


class StringCollector(cst.CSTVisitor):
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
        blacklist = [
            child.body[0].value
            for child in (node.body if isinstance(node, cst.Module)
                          else node.body.children)
            if isinstance(child, cst.SimpleStatementLine)
            and len(child.body) == 1
            and isinstance(child.body[0], cst.Expr)
            and isinstance(child.body[0].value, cst.SimpleString)]
        self.function_stack.append(State(node, blacklist, name))
        self.contexts.append({})

    def pop_context(self) -> None:
        state = self.function_stack.pop()
        context = self.contexts.pop()
        if context:
            # TODO: somehow decorate the name - function name can be the same as
            # a string!
            self.contexts[-1][state.name or state.node.name.value] = context

    def blacklisted(self, node: cst.CSTNode) -> bool:
        return self.function_stack and node in self.function_stack[-1].blacklist

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
        if not translation:
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
            tree = cst.parse_module(f.read())
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
        return yaml.load(open(filename))
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


def main() -> None:
    def add_parser(name, desc):
        subparser = subparsers.add_parser(name, help=desc, description=desc)
        subparser.add_argument(
            "-r", "--root", metavar="root-directory", default="Orange/widgets",
            help="root directory; default='Orange/widgets'")
        subparser.add_argument(
            "-p", "--pattern", default="", metavar="pattern",
            help="include only files whose full path include the pattern")
        return subparser

    argparser = argparse.ArgumentParser()
    subparsers = argparser.add_subparsers(required=True, dest="action")

    parser = add_parser("collect", "Collect message strings in source files")
    parser.add_argument(
        "-o", "--output", required=True, metavar="output-file",
        help="output file")

    parser = add_parser("translate", "Prepare sources with translations")
    parser.add_argument(
        "translations", metavar="translations",
        help="file with translated messages")
    parser.add_argument(
        "-d", "--dest", metavar="destination", required=True,
        help="destination path; root dir will be appended to this path")

    parser = add_parser("update", "Update existing translations with new ones")
    parser.add_argument(
        "new_translations", metavar="new",
        help="new or updated translations")
    parser.add_argument(
        "pot", metavar="existing",
        help="existing translations; "
             "this file is updated unless another output is given")
    parser.add_argument(
        "-o", "--output", metavar="output-file",
        help="output file; if omitted, existing file will updated")

    parser = add_parser("missing", "Prepare a file with missing translations")
    parser.add_argument(
        "translations", metavar="translations",
        help="existing translations")
    parser.add_argument(
        "-m", "--messages", metavar="messages", required=False,
        help="all messages")
    parser.add_argument(
        "-o", "--output", metavar="output-file", required=True,
        help="missing translations")

    args = argparser.parse_args(sys.argv[1:])

    global root_dir
    root_dir = args.root
    pattern = args.pattern

    if args.action == "collect":
        messages = collect(pattern)
        dump(messages, args.output)

    elif args.action == "translate":
        messages = load(args.translations)
        translate(messages, args.dest, pattern)

    elif args.action == "update":
        additional = load(args.new_translations)
        existing = load(args.pot)
        messages = update(existing, additional, pattern)
        dump(messages, args.output or args.pot)

    elif args.action == "missing":
        translations = load(args.translations)
        messages = load(args.messages) if args.messages else translations
        needed = missing(translations, messages, pattern)
        dump(needed, args.output)


if __name__ == "__main__":
    main()
