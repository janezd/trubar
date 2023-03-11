## 0.2.2, 0.2.3 - 2023-03-11

#### New and improved functionality

- (Compatibility breking change) Remove support for yaml-style (`|`) blocks in jaml. Use multiline (single-)quoted strings instead.
- Arguments `-s` and `-d` are now required; trubar no longer falls back to current directory
- If default configuration file is not found in current directory, Trubar also searches the directory with messages and source directory. `.trubarconfig` is now a primary default name.

#### Bug fixes

- `collect` with `--pattern` now keeps original messages from non-matching when updating an existing file
- Replaces Windows-style backslashes with slashes in jaml keys

#### Minor fixes

- Fix message supression in `collect`


## 0.2.1 - 2023-01-13

- `collect` can now update existing files, reducing the need for `merge`
- Minor reorganization of command line arguments

## 0.2 - 2023-01-08

#### New and improved functionality

- A simplified proprietary variation of .jaml with round-trip comments and less need for quotes
- New action `stat`
- Different verbosity levels for `translate` action
- Better error messages about malformed translations
- New option `exclude-pattern` in config files instead of always skipping files whose names begin with "test_".
- New argument `--static` instead of having a path for static files

#### Bug fixes

- Better testing before introducing the f-prefix: if the original already included braces, the f-prefix is not longer added
- Fixed a bug occuring when paths ended with a trailing slash
- Report an error when the source directory does not exist
- Strings that are not translated are no longer reported as rejected in merge