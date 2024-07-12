import os
from typing import Optional

from trubar import actions


def translate(msg_filename: str,
              source_dir: str,
              dest_dir: Optional[str] = None,
              config_file: Optional[str] = None,
              pattern="",
              verbosity=actions.ReportCritical,
              dry_run=False) -> None:
    """
    Translate messages from source directory to destination directory.

    Args:
        msg_filename (str): name of file(s) with messages
        source_dir (str): source directory
        dest_dir (str, optional): target directory, or None for in-place translation
        config_file (str, optional): configuration file; contents override defaults
        pattern (str, optional): pattern for file selection
        verbosity (int, optional): verbosity level
        dry_run (bool, optional): if True, do not write any files
    """
    # do not import at the top level to avoid re-exporting (and shadowing) config
    # pylint: disable=import-outside-toplevel
    from trubar.messages import load
    from trubar.utils import check_any_files
    from trubar.config import config

    if config_file:
        config.update_from_file(config_file)
    if config.languages:
        messages = [
            load(os.path.join(config.base_dir, code, msg_filename))
            if not settings.is_original else {}
            for code, settings in config.languages.items()]
    else:
        messages = [load(msg_filename)]

    trans_keys = set.union(*(set(trans) for trans in messages))
    check_any_files(trans_keys, source_dir)
    actions.translate(messages, source_dir, dest_dir or source_dir, pattern,
                      verbosity=verbosity, dry_run=dry_run)
