## Common Scenarios

### Translations maintenance

As software changes, some messages may change or be removed, and new messages may appear.

To update message file, re-run the collection, specifying the same output file. This will add new messages and keep the existing translations. Any messages that are no longer needed can be recorded in a separate file by pasing an option `-r`.

```
trubar collect -s code/sample -r removed.jaml sample.jaml
```

### Preparing templates

Unlike in our toy example, real projects contain a large proportion of string (one half up to two thirds, in our experience) that must not be translated, such as type annotations in form of strings, various string constants and arguments, old-style named tuple declarations and so forth. Deciding whether a partiuclar string needs translation or not requires looking into code and understanding it.

This presents a huge burden for translator, but can, luckily, be done once for all languages. If a project is translated into one language, we can use

```
trubar template sample.jaml -o template.jaml
```

to prepare a template file `template.jaml` for other languages.

The output file will contain all strings that need attention. See details below.
