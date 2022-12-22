echo "(Configuration)"

echo "... read configuration"
echo "... default is to turn strings to f-strings when needed"
print_run 'trubar translate -s ../test_project -d tmp/test_translated newly_braced.yaml -q'
set +e
grep -q "a = f\"A {'clas' + 's'} attribute\"" tmp/test_translated/__init__.py
if [ $? -ne 0 ]
then
    echo "Invalid initial configuration? String was not changed to f-string"
    exit 1
fi
set -e
rm -r tmp/test_translated

echo "... but this can be disabled in settings"
print_run 'trubar --conf config-no-prefix.yaml translate -s ../test_project -d tmp/test_translated newly_braced.yaml -q'
set +e
grep -q "a = \"A {'clas' + 's'} attribute\"" tmp/test_translated/__init__.py
if [ $? -ne 0 ]
then
    echo "Configuration not read? String was still changed to f-string"
    exit 1
fi
set -e
rm -r tmp/test_translated

echo "... test auto import"
print_run 'trubar --conf config-auto-import.yaml translate -s ../test_project -d tmp/test_translated translations.yaml -q'
if [[ $(cat tmp/test_translated/submodule/apples.py) != "from foo.bar.localization import plurals  # pylint: disable=wrong-import-order

print(\"Pomaranče\")" ]]
then
    echo "Auto import is missing or wrong:"
    echo ""
    cat tmp/test_translated/submodule/apples.py
    echo ""
    exit 1
fi
rm -r tmp/test_translated
