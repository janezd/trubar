import re


class JamlError(Exception):
    pass


def readfile(name, encoding="utf8"):
    with open(name, encoding=encoding) as f:
        return read(f.read())


def read(text):
    return readlines(text.splitlines())


class LineGenerator:
    def __init__(self, lines):
        self.__linegen = iter(lines)
        self.__line_no = 0
        self.__to_yield = None
        self.__go_ahead = True

    @property
    def line_no(self):
        return self.__line_no

    def __prepare(self):
        line = next(self.__linegen)
        self.__line_no += 1
        self.__to_yield = line, len(line) - len(line.lstrip())

    def __iter__(self):
        return self

    def __next__(self):
        if self.__go_ahead:
            self.__prepare()
        self.__go_ahead = True
        return self.__to_yield

    def put_back(self):
        self.__go_ahead = False


def readlines(lines):
    # prevent circular import, pylint: disable=import-outside-toplevel
    from trubar.messages import MsgNode

    def error(msg, line=None):
        raise JamlError(f"Line {line or linegen.line_no}: {msg}") from None

    def read_quoted(line, lineno):
        block = ""
        q, line = line[0], line[1:]
        while (mo := re.match(f"((?:[^{q}]|(?:{q}{q}))*){q}(?!{q})(.*)", line)
                ) is None:
            block += line + "\n"
            try:
                line, _ = next(linegen)
            except StopIteration:
                error(f"file ends before the end of quoted string", lineno)
        inside, after = mo.groups()
        block += inside
        return block.replace(2 * q, q), after

    def read_block(prev_indent, extra_indent):
        if extra_indent.strip():
            try:
                block_indent = prev_indent + int(extra_indent)
            except ValueError:
                error("block indentation must be a number")
        else:
            block_indent = None
        block = ""
        for line, indent in linegen:
            if block_indent is None:
                if not line.strip():
                    continue
                if indent and indent <= prev_indent:
                    raise error("block must be indented")
                block_indent = indent
            elif line.strip():
                if indent < block_indent:
                    linegen.put_back()
                    break
                if block_indent == 0 and line == "|||":
                    break
            block += line[block_indent:] + "\n"
        return block[:-1]

    def check_no_comments():
        if comments:
            error("stray comment", comment_start)

    items = {}
    stack = [(-1, items, True)]
    comments = []
    comment_start = None
    linegen = LineGenerator(lines)
    for line, indent in linegen:
        # Skip empty lines
        if not line.strip():
            continue
        line = line[indent:]

        # Indentation
        last_indent, _, indent_expected = stack[-1]
        if indent_expected:
            if indent <= last_indent:
                error("indent expected")
            stack.append((indent, stack.pop()[1], False))
        elif indent > last_indent:
            error("unexpected indent")
        elif indent < last_indent:
            check_no_comments()
            while stack and indent != stack[-1][0]:
                stack.pop()
            if not stack:
                error("unindent does not match any outer level")

        # Gather comments
        if line[0] == "#":
            comments.append(line)
            comment_start = comment_start or linegen.line_no
            continue

        # Get key
        # Key is quoted
        if line[0] in "'\"":
            key, after = read_quoted(line, linegen.line_no)
            if after[:2] != ": ":
                error("quoted key must be followed by a ': '")
            else:
                value = after[2:].lstrip()
        # block - backward compatibility
        elif line[0] == "|":
            key = read_block(indent, line[1:])
            try:
                line, value_indent = next(linegen)
            except StopIteration:
                error("missing value after block key")
            if value_indent != indent:
                error("value after block key must be aligned with key")
            value = line[indent:]
            if not value.startswith(": "):
                error("block key must be followed by ': '")
            value = value[2:].lstrip()
        # Key is normal
        else:
            mo = re.match(r"(.*?):(?:\s+|$)(.*)", line)
            if mo is None:
                if ":" in line:
                    raise error("colon at the end of the key should be "
                                "followed by a space or a new line")
                else:
                    raise error("key followed by colon expected")
            key, value = mo.groups()

        # Get value
        # `value` is lstripped, but may contain whitespace at the end
        # This is observed in quoted values
        # Leaves
        if value.strip():
            # Value is quoted block
            if value[0] in "'\"":
                value, after = read_quoted(value, linegen.line_no)
                if after.strip():
                    error("quoted value must be followed by end of line")
            # Value is block - for backward compatibility
            elif value[0] in "|":
                value = read_block(indent, value[1:])
            else:
                value = {"true": True, "false": False, "null": None
                         }.get(value.strip(), value)
            stack[-1][1][key] = MsgNode(value, comments or None)
        # Internal nodes
        else:
            space = {}
            stack[-1][1][key] = MsgNode(space, comments or None)
            stack.append((indent, space, True))

        comments = []
        comment_start = None

    if stack[-1][-1]:
        raise error("unexpected end of file")

    check_no_comments()
    return items


def dump(d, indent=""):
    def quotescape(s, allow_colon):
        if "\n" in s \
                or ": " in s and not allow_colon \
                or s[0] in " #\"'|" \
                or s[-1] in " \t\n":
            q = '"' if "'" in s else "'"
            return f"{q}{s.replace(q, 2 * q)}{q}"
        return s

    def dumpval(s):
        trans = {True: "true", False: "false", None: "null", "": '""'}
        if s in trans:
            return trans[s]
        return quotescape(s, True)

    res = ""
    for key, node in d.items():
        if node.comments is not None:
            res += "".join(f"{indent}{comment}\n" for comment in node.comments)
        if isinstance(node.value, dict):
            res += f"{indent}{key}:\n{dump(node.value, indent + '    ')}"
        else:
            res += f"{indent}{quotescape(key, False)}: {dumpval(node.value)}\n"
    return res
