## Trubar

A tool for translation and localization of Python programs via modification of source files.

Trubar supports f-strings and does not require any changes to the original source code, such as marking strings for translation.

#### Installation and use

Use pip to install Trubar

```sh
pip install trubar`
```

Collect all strings in your project by

```sh
trubar collect -s myproject/source -o messages.jaml
```

Add translations to messages.jaml and then run

```sh
trubar translate -s myproject/source -d translated/myproject/source messages.jaml
```

to produce translated source files.

See [Getting Started](http://janezd.github.io/trubar/getting-started) for a slightly longer introduction and complete documentation.