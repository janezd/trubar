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

function report_error_apples() {
    echo $1
    echo ""
    cat tmp/test_translated/submodule/apples.py
    echo ""
    exit 1

}
echo "... test auto import"
print_run 'trubar --conf config-auto-import.yaml translate -s ../test_project -d tmp/test_translated translations.yaml -q'
if [[ $(cat tmp/test_translated/submodule/apples.py) != "from foo.bar.localization import plurals  # pylint: disable=wrong-import-order

print(\"Pomaranče\")" ]]
then
  report_error_apples "Auto import is missing or wrong:"
fi
rm -r tmp/test_translated

echo "... default configuration in current directory"
print_run 'trubar translate -s ../test_project -d tmp/test_translated translations.yaml -q'
if [[ $(cat tmp/test_translated/submodule/apples.py) != "from foo import something_fancy

print(\"Pomaranče\")" ]]
then
    report_error_apples ".trubarconfig.yaml in current directory is not read by default"
fi
rm -r tmp/test_translated

echo "... default configuration in source directory"
mkdir tmp/tmp2
cp -R ../test_project tmp/tmp2/test_project
cp config-auto-import.yaml tmp/tmp2/test_project/.trubarconfig.yaml
cd tmp
print_run 'trubar translate -s tmp2/test_project -d test_translated ../translations.yaml -q'
cd ..
if [[ $(cat tmp/test_translated/submodule/apples.py) != "from foo.bar.localization import plurals  # pylint: disable=wrong-import-order

print(\"Pomaranče\")" ]]
then
    report_error_apples ".trubarconfig.yaml in source directory is not read by default"
fi
rm -r tmp/test_translated
