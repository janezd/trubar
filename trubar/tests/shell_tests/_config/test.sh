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

function check_apples() {
    if [[ $(head -1 tmp/test_translated/submodule/apples.py) != $1 ]]
        then
            echo "Config not imported"
            echo ""
            cat tmp/test_translated/submodule/apples.py
            echo ""
            exit 1
        fi
}

echo "... test auto import"
print_run 'trubar --conf config-auto-import.yaml translate -s ../test_project -d tmp/test_translated translations.yaml -q'
check_apples "from foo.bar.localization import plurals  # pylint: disable=wrong-import-order"
rm -r tmp/test_translated

echo "... default configuration in current directory"
print_run 'trubar translate -s ../test_project -d tmp/test_translated translations.yaml -q'
check_apples "from foo import something_fancy"
rm -r tmp/test_translated

# Copy project to another location so we can play with adding config file
mkdir tmp/tmp2
cp -R ../test_project tmp/tmp2/test_project

echo "... default configuration in messages directory"
cd tmp
print_run 'trubar translate -s tmp2/test_project -d test_translated ../translations.yaml -q'
cd ..
check_apples "from foo import something_fancy"

echo "... default configuration in source directory"
cp config-auto-import.yaml tmp/tmp2/test_project/.trubarconfig.yaml
mv .trubarconfig.yaml .trubarconfig.bak
cd tmp
print_run 'trubar translate -s tmp2/test_project -d test_translated ../translations.yaml -q'
cd ..
mv .trubarconfig.bak .trubarconfig.yaml
check_apples "from foo.bar.localization import plurals  # pylint: disable=wrong-import-order"
rm -r tmp/test_translated tmp/tmp2

