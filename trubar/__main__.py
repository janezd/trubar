import argparse
import os
import sys

from trubar.actions import \
    collect, translate, merge, missing, template, stat, \
    ReportCritical
from trubar.messages import load, dump
from trubar.config import config
from trubar.utils import check_any_files, dump_removed


def check_dir_exists(path):
    if not os.path.isdir(path):
        if os.path.exists(path):
            print(f"{path} is not a directory.")
        else:
            print(f"Directory {path} does not exist.")
        sys.exit(2)


def load_config(args):
    if args.conf:
        config.update_from_file(args.conf)
        return

    paths = [""]
    if getattr(args, "messages", False):
        paths.append(os.path.split(args.messages)[0])
    if getattr(args, "source", False):
        paths.append(args.source)
    for path in paths:
        for name in (".trubarconfig.yaml", "trubar-config.yaml"):
            fullname = os.path.join(path, name)
            if os.path.exists(fullname):
                config.update_from_file(fullname)
                return


def main() -> None:
    def add_parser(name, desc):
        subparser = subparsers.add_parser(name, help=desc, description=desc)
        subparser.add_argument(
            "-p", "--pattern", default="", metavar="pattern",
            help="include only files whose full path include the pattern")
        return subparser

    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--conf", default="", metavar="configuration-file",
        help="configuration file")
    subparsers = argparser.add_subparsers(required=True, dest="action")

    parser = add_parser("collect", "Collect message strings in source files")
    parser.add_argument(
        "-s", "--source", metavar="source-dir",
        required=True, help="source path")
    parser.add_argument(
        "-u", "--newer", action="store_true",
        help="check only source files that are newer than the message file")
    parser.add_argument(
        "messages", metavar="messages",
        help="existing or new file with messages")
    parser.add_argument(
        "-r", "--removed", metavar="removed-translations", default=None,
        help="file for removed translations, if any")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="supress intermediary outputs")
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="don't write the output file; removed translations (if any) are written"
    )

    parser = add_parser("translate", "Prepare sources with translations")
    parser.add_argument(
        "messages", metavar="messages",
        help="file with translated messages")
    parser.add_argument(
        "-d", "--dest", metavar="destination-dir",
        help="destination path")
    parser.add_argument(
        "-i", "--inplace", action="store_true",
        help="translate files in-place")
    parser.add_argument(
        "-s", "--source", metavar="source-dir",
        required=True, help="source path")
    parser.add_argument(
        "--static", metavar="static-files-dir", action="append",
        help="directory(-ies) with static files to copy")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="supress intermediary outputs")
    parser.add_argument(
        "-v", "--verbosity", type=int, choices=range(4), default=1,
        help="verbosity (0=quiet, 1=updates, 2=translations, 3=all")
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="don't write anything; perform a trial run to check the structure"
    )

    parser = add_parser("merge",
                        "Merge translations into template or existing "
                        "translations")
    parser.add_argument(
        "translations", metavar="translations",
        help="new or updated translations")
    parser.add_argument(
        "messages", metavar="messages",
        help="file with messages; this file is updated unless --output is given")
    parser.add_argument(
        "-o", "--output", metavar="output-file",
        help="output file; if omitted, existing file will updated")
    parser.add_argument(
        "-u", "--unused", metavar="unused", default=None,
        help="file for unused translations (if any)")
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="run without writing anything"
    )

    parser = add_parser("template",
                        "Create empty template from existing translations")
    parser.add_argument(
        "messages", metavar="translations",
        help="file with existing translations for another language")
    parser.add_argument(
        "-o", "--output", metavar="output-file", required=True,
        help="output file")

    parser = add_parser("missing", "Prepare a file with missing translations")
    parser.add_argument(
        "messages", metavar="messages",
        help="file with existing translations")
    parser.add_argument(
        "-m", "--all-messages", metavar="all-messages", required=False,
        help="all messages")
    parser.add_argument(
        "-o", "--output", metavar="output-file", required=True,
        help="missing translations")

    parser = add_parser("stat", "Show statistics about messages in the file")
    parser.add_argument(
        "messages", metavar="messages",
        help="file with messages")

    args = argparser.parse_args(sys.argv[1:])
    load_config(args)
    pattern = args.pattern

    if args.action == "collect":
        min_time = None
        check_dir_exists(args.source)
        if os.path.exists(args.messages):
            existing = load(args.messages)
            check_any_files(set(existing), args.source)
            if args.newer:
                min_time = os.stat(args.messages).st_mtime
        else:
            existing = {}
        messages, removed = collect(args.source, existing, pattern,
                                    quiet=args.quiet, min_time=min_time)
        if not args.dry_run:
            dump(messages, args.messages)
        dump_removed(removed, args.removed, args.messages)

    elif args.action == "translate":
        check_dir_exists(args.source)
        if args.inplace:
            if args.dest:
                argparser.error("options -d and -i are incompatible")
            else:
                args.dest = args.source
        elif not args.dest:
            argparser.error("specify destination (-d) or translate in place (-i)")
        if args.static:
            config.set_static_files(args.static)
        verbosity = ReportCritical if args.quiet else args.verbosity
        if config.languages:
            messages = [
                load(os.path.join(config.base_dir, code, args.messages))
                if not settings.is_original else {}
                for code, settings in config.languages.items()]
        else:
            messages = [load(args.messages)]
        trans_keys = set.union(*(set(trans) for trans in messages))
        check_any_files(trans_keys, args.source)
        translate(
            messages, args.source, args.dest, pattern,
            verbosity=verbosity, dry_run=args.dry_run)

    elif args.action == "merge":
        additional = load(args.translations)
        existing = load(args.messages)
        unused = merge(additional, existing, pattern,
                       print_unused=not args.unused)
        if not args.dry_run:
            dump(existing, args.output or args.messages)
        if args.unused and unused:
            dump(unused, args.unused)

    elif args.action == "template":
        existing = load(args.messages)
        new = template(existing, pattern)
        dump(new, args.output)

    elif args.action == "missing":
        translations = load(args.messages)
        messages = load(args.all_messages) \
            if args.all_messages else translations
        needed = missing(translations, messages, pattern)
        dump(needed, args.output)

    elif args.action == "stat":
        messages = load(args.messages)
        stat(messages, pattern)


if __name__ == "__main__":
    main()
