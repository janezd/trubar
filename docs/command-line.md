## Command line actions and their arguments

Trubar is invoked by

`trubar <common-arguments> <action> <arguments>`

**Common arguments** are

`-h`
: Prints help and exits.

`--conf <conf-file>`
: Specifies the [configuration file](../configuration). If not given, Trubar searches for `.trubarconfig.yaml` and `trubar-config.yaml` in current directory, directory with messages, and in source directory (for `collect` and `translate`).

Action must be one of the following:

- **collect:** collects strings from the specified source tree,
- **translate:** copies the source tree and replaces strings with their translations,
- **missing:** prepares a file that contains untranslated messages from another message file (i.e., those with `null` translations),
- **merge:** inserts translations from one message file into another,
- **template:** uses translations into one language to prepare a template for another,
- **stat:** reports on the number of type of translations.


### Collect

```
trubar collect [-h] [-p pattern] [-r removed-translations] [-q] [-n]
               -s source-dir messages
```

Collects strings from the specified source tree, skipping files that don't end with `.py` or whose path includes `tests/test_`. (The latter can be changed in [configuration file](../configuration).) Strings with no effect are ignored; this is aimed at docstrings, but will also skip any other unused strings.

If the output file already exists, it is updated: new messages are merged into it, existing translations are kept, and obsolete messages are removed. The latter can be recorded using the option `-r`.

`messages`
: The name of the file with messages (preferrably .jaml). If the file does not exist, it is created, otherwise it is updated with new messages and obsolete
messages are removed.

`-s <path>`, `--source <path>`
: Defines the root directory of the source tree.

`-p <pattern>`, `--pattern <pattern>`
: Gives a pattern that the file path must include to be considered. The pattern is checked against the entire path; e.g. `-p rm/pi` would match the path `farm/pigs.py:`.

`-r <removed-translations>`, `--removed <removed-translations>`
: The name of the file for messages that were present in the messages file but no longer needed.

`-n`, `--dry-run`: Run, but do not change the output file. The file with removed messages is still written.

`-q`, `--quiet`
: Supresses the output, except critical error messages.


### Translate

```
trubar translate [-h] [-p pattern] [--static static-files-dir]
                 [-q] [-v {0,1,2,3}] [-n]
                 -s source-dir -d destination-dir messages
```

Translates files with extension .py and writes them to destination directories, and copies all other files. Alternatively, `-i` can be given for translation in-place. Untranslated strings (marked `null`, `false` or `true`) are kept as they are. The action overwrites any existing files.

`messages`
: the name of the file with translated messages.

`-s <source-dir>`, `--source <source-dir>`
: Root directory of the source tree.

`-d <dest-path>`, `--dest <dest-path>`
: Destination directory. Either this option or `-i` is required.

`-i`, `--inplace`
: In-place translation. Either this or `-d` is required.

`-p <pattern>`, `--pattern <pattern>`
: A pattern that the file path must include to be considered.

`--static <static-files-path>`
: Copies the file from the given path into destination tree; essentially `cp -R <static-files-path> <dest-path>/<static-file-path>`. This is used, for instance, for [adding modules with target-language related features](../localization/#plural-forms), like those for plural forms. This option can be given multiple times. If given, this argument overrides `static-files` from config file.

`-q`, `--quiet`
: Supresses output messages, except for critical. Overrides option `-v`.

`-v <level>`, `--verbosity <level>`
: Sets the verbosity level to `0` (critical messages, equivalent to `-q`), `1` (report on files that are created or updated), `2` (also list files that have not changed) or `3` (report on all files, including those merely copied). This option is ignored in presence of `-q`.

`-n`, `--dry-run`
: Run, but do not write anything.


### Merge

```
trubar merge [-h] [-o output-file] [-u unused] [-p pattern] [-n]
             translations messages
```

Merges translations into message file.

`translations` (required)
: The "source" file with translations.

`messages` (required)
: File with messages into which the translations from `translations` are merged. This file is modified unless another output file is given.

`-o <output-file>`, `--output <output-file>`
: The output file name; if omitted, the file given as `destination` is changed.

`-u <unused>`, `--unused <unused>`
: A name of the file for messages that no longer appear in the sources.

`-p <pattern>`, `--pattern <pattern>`
: A pattern that the file path must include to be considered.

`-n`, `--dry-run`
: Run, but do not write anything.

### Missing

```
trubar missing [-h] [-p pattern] [-m all-messages] -o output-file
               messages
```

Prepare a file with missing translations. A translation is missing if the translated message is `null`. Alternatively, the user can pass a file with all messages (option `-m`), and the translation is missing if the translated file either does not include it or has a `null` translation.

`messages` (required)
: The name of the file with messages.

`-o <output-file>`, `--output <output-file>` (required)
: The name of the output file.

`-m <msg-file>`, `--all-messages <msg-file>`
: If given, this file is considered to contain all messages.

`-p <pattern>`, `--pattern <pattern>`
: If given, the output file will only contain messages from source files whose paths include the pattern.

### Template

```
trubar template [-h] [-p pattern] -o output-file messages
```

Create a template from existing translations. The output file will contain all strings that need attention.

- Strings that are "translated" to `false` are skipped, because they must not be translated.
- Strings that are "translated" to `true` are retained as they are. `true` indicates that they should probably be kept, but may also be translated if needed.
- If string is translated, the original is kept, but translation is replaced by `null`.
- Strings that are not translated (`null`) are kept.

`messages` (required)
: Existing (preferrably complete) translations into some language.

`-o <output-file`, `--output <output-file>` (required)
: Output file name.

`-p <pattern>`, `--pattern <pattern>`
: If given, the output file will only contain messages from source files whose paths include the pattern.

### Stat

```
trubar stat [-h] [-p pattern] messages
```

Print statistics about messages in the given file.

Here's an example output.

`messages`
: File with messages.

`-p <pattern>`, `--pattern <pattern>`
: If given, the count will include files whose paths include the pattern.

```
Total messages: 11161

Translated:       3257    29.2%
Kept unchanged:    313     2.8%
Programmatic:     7065    63.3%
Total completed: 10635    95.3%

Untranslated:      526     4.7%
```

Translated messages are those with actual translations, unchanged are translated as `true` and "programmatic" as `false`. "Untranslated" messages are those that are still marked as `null` and require translations.

