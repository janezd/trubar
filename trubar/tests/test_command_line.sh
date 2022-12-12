function print_run() {
    echo "> " $1
    if [ -z $2 ]
    then
        ${1}
    else
        ${1} > $2
    fi
}

cd trubar/tests

# Remove anything that could remain from previous runs
rm -f messages.yaml
rm -rf test_translations
rm -rf si_translations_copy
rm -f updated_translations.yaml rejected.yaml errors.txt
rm -f translations-copy.yaml
rm -f missing.yaml
rm -f template.yaml


(
set -e
echo "Collect"
print_run 'trubar collect -s test_project -o messages.yaml -q'
diff messages.yaml test_project/all_messages.yaml
if [ -n "`trubar collect -s test_project -o messages.yaml -q`" ]
then
  echo "Not quiet."
  exit 1
fi
if [ -z "`trubar collect -s test_project -o messages.yaml`" ]
then
  echo "Not loud."
  exit 1
fi
rm messages.yaml

echo "... with pattern"
print_run 'trubar collect -s test_project -o messages.yaml -p submodule -q'
diff messages.yaml test_project/submodule_messages.yaml
rm messages.yaml

echo "... invalid source dir"
set +e
print_run 'trubar collect -s test_project/__init__.py -o messages.yaml -q' /dev/null
if [ $? -eq 0 ]
then
    echo "Non-zero exit code expected"
    exit 1
fi
print_run 'trubar collect -s test_project_not -o messages.yaml -q' /dev/null
if [ $? -eq 0 ]
then
    echo "Non-zero exit code expected"
    exit 1
fi
set -e


echo
echo "Translate"
cp -r si_translations si_translations_copy
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -q'
diff -r -x "*.yaml" -x "*.txt" test_translations si_translations
diff -r si_translations si_translations_copy
rm -r test_translations

echo "... with pattern"
mkdir test_translations
cp test_project/__init__.py test_translations/__init__.py
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -p submodule -q'
diff -r test_translations/submodule si_translations/submodule
diff test_translations/__init__.py test_project/__init__.py
diff -r si_translations si_translations_copy
rm -r test_translations

echo "... with static files"
mkdir test_translations
cp test_project/__init__.py test_translations/__init__.py
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -p submodule -q --static static_files_lan'
diff -r test_translations/a static_files_lan/a
rm -r test_translations

echo "... dry run"
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -q -n --static static_files_lan'
diff -r si_translations si_translations_copy
if [ -d test_translations ]
then
  echo "Not dry."
  exit 1
fi
rm -r si_translations_copy

echo "... verbosity"
print_run 'trubar translate -s test_project -d si_translations_half test_project/translations.yaml -n -v 3' verb_output
diff verb_output verbosity_outputs/3.txt
print_run 'trubar translate -s test_project -d si_translations_half test_project/translations.yaml -n -v 2' verb_output
diff verb_output verbosity_outputs/2.txt
print_run 'trubar translate -s test_project -d si_translations_half test_project/translations.yaml -n -v 1' verb_output
diff verb_output verbosity_outputs/1.txt
print_run 'trubar translate -s test_project -d si_translations_half test_project/translations.yaml -n -v 0' verb_output
if [[ ! -z $(cat verb_output) ]] ; then
    echo "not quiet"
    exit 1
fi
print_run 'trubar translate -s test_project -d si_translations_half test_project/translations.yaml -n -q' verb_output
if [[ ! -z $(cat verb_output) ]] ; then
    echo "not quiet"
    exit 1
fi
print_run 'trubar translate -s test_project -d si_translations test_project/translations.yaml -n -v 1' verb_output
diff verb_output verbosity_outputs/nochanges.txt
print_run 'trubar translate -s test_project -d si_translations test_project/translations.yaml -n -v 0' verb_output
if [[ ! -z $(cat verb_output) ]] ; then
    echo "not quiet"
    exit 1
fi
rm verb_output

echo
echo "Merge"
cp test_project/translations.yaml translations-copy.yaml
print_run 'trubar merge test_project/new_translations.yaml test_project/translations.yaml -o updated_translations.yaml'
diff test_project/translations.yaml translations-copy.yaml
diff updated_translations.yaml test_project/updated_translations.yaml
rm updated_translations.yaml

echo "... in place"
cp test_project/translations.yaml translations-copy.yaml
print_run 'trubar merge test_project/new_translations.yaml test_project/translations.yaml'
diff test_project/translations.yaml test_project/updated_translations.yaml
mv translations-copy.yaml test_project/translations.yaml

echo "... with pattern"
print_run 'trubar merge test_project/new_translations.yaml test_project/translations.yaml -o updated_translations.yaml -p submodule'
diff updated_translations.yaml test_project/updated_translations_submodule.yaml
rm updated_translations.yaml

echo "... with errors"
cp test_project/translations.yaml translations-copy.yaml
print_run 'trubar merge test_project/faulty_translations.yaml test_project/translations.yaml -o updated_translations.yaml -r rejected.yaml' 'errors.txt'
diff test_project/translations.yaml translations-copy.yaml
diff updated_translations.yaml test_project/updated_translations_faulty.yaml
diff rejected.yaml test_project/rejected.yaml
diff errors.txt test_project/errors.txt
rm updated_translations.yaml rejected.yaml errors.txt

echo "... dry-run, with errors"
cp test_project/translations.yaml translations-copy.yaml
print_run 'trubar merge test_project/faulty_translations.yaml test_project/translations.yaml -r rejected.yaml -n' 'errors.txt'
diff test_project/translations.yaml translations-copy.yaml
diff rejected.yaml test_project/rejected.yaml
diff errors.txt test_project/errors.txt
rm  translations-copy.yaml rejected.yaml errors.txt

echo
echo "Missing"
echo "... all missing"
print_run 'trubar missing test_project/all_messages.yaml -o missing.yaml'
diff missing.yaml test_project/all_messages.yaml
rm missing.yaml

echo "... some missing"
print_run 'trubar missing test_project/translations.yaml -o missing.yaml'
diff missing.yaml test_project/missing.yaml
rm missing.yaml

echo "... some missing, pattern"
print_run 'trubar missing test_project/translations.yaml -o missing.yaml -p trash'
diff missing.yaml test_project/missing_trash.yaml
rm missing.yaml

echo "... given all messages"
print_run 'trubar missing test_project/translations.yaml  -m test_project/all_messages.yaml -o missing.yaml'
diff missing.yaml test_project/missing.yaml
rm missing.yaml

echo "... given all messages and pattern"
print_run 'trubar missing test_project/translations.yaml  -m test_project/all_messages.yaml -o missing.yaml -p trash'
diff missing.yaml test_project/missing_trash.yaml
rm missing.yaml

echo
echo "Template"
print_run 'trubar template test_project/translations_for_template.yaml -o template.yaml'
diff template.yaml test_project/template.yaml
rm template.yaml

echo
echo "Stat"
print_run 'trubar stat test_project/translations.yaml' /dev/null
print_run 'trubar stat test_project/translations.yaml -p submodule' /dev/null
print_run 'trubar stat test_project/translations.yaml -p nomodule' /dev/null

echo
echo "Checks for file sanity"
set +e
print_run 'trubar missing test_project/bad_structure.yaml -o missing.yaml' errors_structure.txt
if [ $? -eq 0 ]
then
    echo "Non-zero exit code expected"
    exit 1
fi
set -e
diff errors_structure.txt test_project/errors_structure.txt
rm errors_structure.txt

echo
echo "Read configuration"
echo "... default is to turn strings to f-strings when needed"
print_run 'trubar translate -s test_project -d test_translations test_project/newly_braced.yaml -q'
set +e
grep -q "a = f\"A {'clas' + 's'} attribute\"" test_translations/__init__.py
if [ $? -ne 0 ]
then
    echo "Invalid initial configuration? String was not changed to f-string"
    exit 1
fi
set -e

echo "... but this can be disabled in settings"
print_run 'trubar --conf test_project/config-no-prefix.yaml translate -s test_project -d test_translations test_project/newly_braced.yaml -q'
set +e
grep -q "a = \"A {'clas' + 's'} attribute\"" test_translations/__init__.py
if [ $? -ne 0 ]
then
    echo "Configuration not read? String was still changed to f-string"
    exit 1
fi
set -e
rm -r test_translations

echo "... test auto import"
print_run 'trubar --conf test_project/config-auto-import.yaml translate -s test_project -d test_translations test_project/translations.yaml -q'
if [[ $(cat test_translations/submodule/apples.py) != "from foo.bar.localization import plurals  # pylint: disable=wrong-import-order

print(\"Pomaranče\")" ]]
then
    echo "Auto import is missing or wrong:"
    echo ""
    cat test_translations/submodule/apples.py
    echo ""
    exit 1
fi
rm -r test_translations

echo
echo "Done."
)

cd - > /dev/null