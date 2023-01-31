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

    def read_triple_quoted_block(line, lineno):
        block = ""
        quotes, line = line[:3], line[3:]
        while quotes not in line:
            block += line + "\n"
            try:
                line, _ = next(linegen)
            except StopIteration:
                error(f"file ends before the end of triple-quoted block",
                      lineno)
        inside, _, after = line.partition(quotes)
        block += inside
        return block.replace(("\\" + quotes[0]) * 3, quotes), after

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

        # Get key and value
        # Key is triple-quoted block
        if line[:3] in ("'''", '"""'):
            key, after = read_triple_quoted_block(line, linegen.line_no)
            if after[:2] != ": ":
                error("triple-quoted key must be followed by a ': '")
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
        # Key is quoted
        elif line[0] in "\"'":
            q = line[0]
            mo = re.match(
                rf"{q}(?P<key>([^{q}]|({q}{q}))*?){q}\s*:\s+(?P<value>.*)",
                line)
            if mo is None:
                raise error("invalid quoted key")
            key, value = mo.group("key", "value")
            key = key.replace(2 * q, q)
        # Key is normal
        else:
            mo = re.match(r"(.*?):(\s+|$)(.*)", line)
            if mo is None:
                if ":" in line:
                    raise error("colon at the end of the key should be "
                                "followed by a space or a new line")
                else:
                    raise error("key followed by colon expected")
            key, _, value = mo.groups()

        # `value` is lstripped, but may contain whitespace at the end
        # This is needed for triple-quoted values
        # Leaves
        if svalue := value.strip():
            # Value is triple-quoted block
            if value[:3] in ("'''", '"""'):
                value, after = read_triple_quoted_block(value, linegen.line_no)
                if after.strip():
                    error("triple-quoted value must be followed by end of line")
            # Value is block - for backward compatibility
            elif value[0] in "|":
                value = read_block(indent, value[1:])
            # value is quoted
            elif _is_quoted_value(svalue):
                value = svalue[1:-1]
            else:
                value = {"true": True, "false": False, "null": None
                         }.get(svalue, value)
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
    def dumpb(s):
        q = "'''" if '"""' in s else '"""'
        s.replace(q, ("\\" + q[0]) * 3)
        return f"{q}{s}{q}"

    def dumpkey_msg(s):
        if "\n" in s:
            return dumpb(s)
        if ": " in s or s[0] in " #\"'|" or s[-1] == " ":
            q = '"' if "'" in s else "'"
            return f"{q}{s.replace(q, 2 * q)}{q}"
        return s

    def dumpval(s):
        trans = {True: "true", False: "false", None: "null",
                 "": '""', "|": '"|"'}
        if s in trans:
            return trans[s]
        if "\n" in s[1:-1] and len(s) > 80:
            return dumpb(s)
        # if value would be recognized as quoted, it must be quoted
        # leading or trailing spaces also require quoting
        if _is_quoted_value(s) or s[0] == " " or s[-1] == " ":
            q = '"' if s[0] == "'" else "'"
            return q + s + q
        return s

    res = ""
    for key, node in d.items():
        if node.comments is not None:
            res += "".join(f"{indent}{comment}\n" for comment in node.comments)
        if isinstance(node.value, dict):
            res += f"{indent}{key}:\n{dump(node.value, indent + '    ')}"
        else:
            res += f"{indent}{dumpkey_msg(key)}: {dumpval(node.value)}\n"
    return res


def _is_quoted_value(value):
    return len(value) > 1 and value[0] in "\"'" and value[-1] == value[0]
