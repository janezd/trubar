## Command line actions and their arguments

Trubar is invoked by

`trubar <common-arguments> <action> <arguments>`

**Common arguments** are

`-h`
: Prints help and exits.

`--conf <conf-file>`
: Specifies the [configuration file](/configuration).

Action must be one of the following:

- **collect:** collects strings from the specified source tree,
- **translate:** copies the source tree and replaces strings with their translations,
- **missing:** prepares a file that contains untranslated messages from another message file (i.e., those with `null` translations),
- **merge:** inserts translations from one message file into another,
- **template:** uses translations into one language to prepare a template for another,
- **stat:** reports on the number of type of translations.


### Collect

```
trubar collect [-h] [-s source-dir] [-p pattern]
                -o output-file [-q]
```

Collects strings from the specified source tree, skipping files that don't end with `.py` or whose path includes `tests/test_`. (The latter can be changed in [configuration file](/configuration).) Strings with no effect are ignored; this is aimed at docstrings, but will also skip any other unused strings.


`-s <path>`, `--source <path>`
: Defines the root directory of the source tree. Default is the current directory.

`-p <pattern>`, `--pattern <pattern>`
: Gives a pattern that the file path must include to be considered. The pattern is checked against the entire path; e.g. `-p rm/pi` would match the path `farm/pigs.py:`.

`-o <output-file>`, `--output <output-file>` (required)
: The name of the output file; extension should be .jaml (preferred) or .yaml.

`-q`, `--quiet`
: Supresses the output, except critical error messages.


### Translate

```
trubar translate [-h] [-s source-dir] [-d destination-dir]
                 [-p pattern]
                 [--static static-files-dir]
                 [-q] [-v {0,1,2,3}] [-n]
                 translations
```

Translates files with extension .py and writes them to destination directories, and copies all other files. Untranslated strings (marked `null`, `false` or `true`) are kept as they are. The action overwrites any existing files.

`translations` (required)
: the name of the file with translated messages.

`-s <source-path>`, `--source <source-path>`
: Root directory of the source tree. Default is the current directory.

`-d <dest-path>`, `--dest <dest-path>` (required)
: Destination directory.

`-p <pattern>`, `--pattern <pattern>`
: A pattern that the file path must include to be considered.

`--static <static-files-path>`
: Copies the file from the given path into destination tree; essentially `cp -R <static-files-path> <dest-path>/<static-file-path>`. This is used for [adding modules with target-language related features](/localization/#plural-forms), like those for plural forms.

`-q`, `--quiet`
: Supresses output messages, except for critical. Overrides option `-v`.

`-v <level>`, `--verbosity <level>`
: Sets the verbosity level to `0` (critical messages, equivalent to `-q`), `1` (report on files that are created or updated), `2` (also list files that have not changed) or `3` (report on all files, including those merely copied). This option is ignored in presence of `-q`.

`-n`, `--dry-run`
: Run, but do not write anything.

### Merge

```
trubar merge [-h] [-o output-file] [-r rejected-file]
                  [-p pattern] [-n]
                   new existing
```

Merges translations into another message file. After a new release of the package, one can use `collect` to extract the current set of messages, and `merge` to merge existing translations into it.

`source` (required)
: The "source" file with translations.

`destination` (required)
: Destination file into which we won't to insert the source translations.

`-o <output-file>`, `--output <output-file>`
: The output file name; if omitted, the file given as `destination` is changed.

`-r <rejected>`, `--rejected <rejected>`
: A name of the file for messages that no longer appear in the sources.

`-p <pattern>`, `--pattern <pattern>`
: A pattern that the file path must include to be considered.

`-n`, `--dry-run`
: Run, but do not write anything.

### Missing

```
trubar missing [-h] [-p pattern] [-m messages] -o output-file
                      translations
```

Prepare a file with missing translations. A translation is missing if the translated message is `null`. Alternatively, the user can pass a file with all messages (option `-m`), and the translation is missing if the translated file either does not include it or has a `null` translation.

`translations` (required)
: The name of the file with messages.

`-o <output-file>`, `--output <output-file>` (required)
: The name of the output file.

`-m <msg-file>`, `--messages <msg-file>`
: If given, this file is considered to contain all messages.

`-p <pattern>`, `--pattern <pattern>`
: If given, the output file will only contain messages from source files whose paths include the pattern.

### Template

```
trubar template [-h] [-p pattern] -o output-file translations
```

Create a template from existing translations. The output file will contain all strings that need attention.

- Strings that are "translated" to `false` are skipped, because they must not be translated.
- Strings that are "translated" to `true` are retained as they are. `true` indicates that they should probably be kept, but may also be translated if needed.
- If string is translated, the original is kept, but translation is replaced by `null`.
- Strings that are not translated (`null`) are kept.

`translations` (required)
: Existing (preferrably complete) translations into some language.

`-o <output-file`, `--output <output-file>` (required)
: Output file name.

`-p <pattern>`, `--pattern <pattern>`
: If given, the output file will only contain messages from source files whose paths include the pattern.

### Stat

```
trubar stat [-h] [-p pattern] message-file
```

Print statistics about messages in the given file.

Here's an example output.

`message-file` (required)
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

