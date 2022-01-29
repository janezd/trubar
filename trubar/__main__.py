import argparse
import sys

from trubar.actions import *


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

    set_root_dir(args.root)
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
