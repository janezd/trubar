import argparse
import os
import sys

from trubar.actions import \
    collect, translate, merge, missing, template, stat, \
    ReportCritical
from trubar.messages import load, dump
from trubar.config import config


def check_dir_exists(path):
    if not os.path.isdir(path):
        if os.path.exists(path):
            print(f"{path} is not a directory.")
        else:
            print(f"Directory {path} does not exist.")
        sys.exit(2)


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
        "-s", "--source", metavar="source-dir", default=".", help="source path")
    parser.add_argument(
        "-o", "--output", required=True, metavar="output-file",
        help="output file")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="supress intermediary outputs")

    parser = add_parser("translate", "Prepare sources with translations")
    parser.add_argument(
        "translations", metavar="translations",
        help="file with translated messages")
    parser.add_argument(
        "-d", "--dest", metavar="destination-dir", help="destination path")
    parser.add_argument(
        "-s", "--source", metavar="source-dir", help="source path")
    parser.add_argument(
        "--static", metavar="static-files-dir",
        help="directory with static files to copy")
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
        "new_translations", metavar="new",
        help="new or updated translations")
    parser.add_argument(
        "pot", metavar="existing",
        help="existing translations; "
             "this file is updated unless another output is given")
    parser.add_argument(
        "-o", "--output", metavar="output-file",
        help="output file; if omitted, existing file will updated")
    parser.add_argument(
        "-r", "--rejected", metavar="rejected-file", default=None,
        help="file for rejected translations (if any)")
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="don't change translations file, just check the structure"
    )

    parser = add_parser("template",
                        "Create empty template from existing translations")
    parser.add_argument(
        "translations", metavar="translations",
        help="existing translations for another language")
    parser.add_argument(
        "-o", "--output", metavar="output-file", required=True,
        help="output file")

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

    parser = add_parser("stat", "Show statistics about messages in the file")
    parser.add_argument(
        "messages", metavar="messages",
        help="file with messages")

    args = argparser.parse_args(sys.argv[1:])

    if args.conf:
        config.update_from_file(args.conf)
    elif os.path.exists("trubar-config.yaml"):
        config.update_from_file("trubar-config.yaml")

    pattern = args.pattern

    if args.action == "collect":
        check_dir_exists(args.source)
        messages = collect(args.source, pattern, quiet=args.quiet)
        dump(messages, args.output)

    elif args.action == "translate":
        check_dir_exists(args.source)
        if not (args.source or args.dest) and not args.dry_run:
            argparser.error("at least one of --source and --dest required")
        if args.source == args.dest:
            argparser.error("source and destination must not be the same")
        if args.static:
            config.set_static_files(args.static)
        verbosity = ReportCritical if args.quiet else args.verbosity
        messages = load(args.translations)
        translate(messages, args.source, args.dest, pattern,
                  verbosity=verbosity, dry_run=args.dry_run)

    elif args.action == "merge":
        additional = load(args.new_translations)
        existing = load(args.pot)
        rejected = merge(additional, existing, pattern,
                         print_rejections=bool(args.rejected))
        if not args.dry_run:
            dump(existing, args.output or args.pot)
        if args.rejected and rejected:
            dump(rejected, args.rejected)

    elif args.action == "template":
        existing = load(args.translations)
        new = template(existing, pattern)
        dump(new, args.output)

    elif args.action == "missing":
        translations = load(args.translations)
        messages = load(args.messages) if args.messages else translations
        needed = missing(translations, messages, pattern)
        dump(needed, args.output)

    elif args.action == "stat":
        messages = load(args.messages)
        stat(messages, pattern)


if __name__ == "__main__":
    main()
