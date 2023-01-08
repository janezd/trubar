## 0.2 - 2022-01-08

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