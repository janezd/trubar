## Common Scenarios

### Translations maintenance

As software changes, some messages may change or be removed, and new messages may appear.

Say that a new release of `sample` starts with

```python
    print("This program serves no useful purpose.")
```

and `"Wrong number: {n} is not between 5 and 20."` was kindly changed to `"Wrong number: {n} must be between 5 and 20."`.

To update translations, we do the following:

```
trubar collect -s code/sample -o new-sample.jaml
trubar merge sample.jaml new-sample.jaml
```

`collect` collects new messages and `merge` merges existing translations into new messages. We can then edit `new-sample.jaml` and at the end rename them to `sample.jaml`, or first rename and then edit.

(This process is too complicated; a simplification is planned soon.)


### Preparing templates

Unlike in our toy example, real projects contain a large proportion of string (one half up to two thirds, in our experience) that must not be translated, such as type annotations in form of strings, various string constants and arguments, old-style named tuple declarations and so forth. Deciding whether a partiuclar string needs translation or not requires looking into code and understanding it.

This presents a huge burden for translator, but can, luckily, be done once for all languages. If a project is translated into one language, we can use

```
trubar template sample.jaml -o template.jaml
```

to prepare a template file `template.jaml` for other languages.

The output file will contain all strings that need attention. See details below.
