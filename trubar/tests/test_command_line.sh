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

echo "... dry run"
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -q -n'
diff -r si_translations si_translations_copy
if [ -d test_translations ]
then
  echo "Not dry."
  exit 1
fi

echo "... faulty translations"
print_run 'trubar translate -s test_project -d test_translations test_project/faulty_translations.yaml -q'
diff -r si_translations/submodule/apples.py test_translations/submodule/apples.py
if [ -f test_translations/__init__.py ]
then
  echo "Wrote errored file."
  exit 1
fi
if [ -f test_translations/trash/nothing.py ]
then
  echo "Wrote errored file."
  exit 1
fi
rm -r test_translations
rm -r si_translations_copy

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
echo "Done."
)

cd - > /dev/null