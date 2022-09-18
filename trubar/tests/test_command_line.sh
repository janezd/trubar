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

(
set -e
echo "Collect"
print_run 'trubar collect -s test_project -o messages.yaml -q'
diff messages.yaml test_project/all_messages.yaml
if [ -n "`trubar collect -s test_project -o messages.yaml -q`" ]
then
  echo "Not quiet."
fi
if [ -z "`trubar collect -s test_project -o messages.yaml`" ]
then
  echo "Not loud."
fi
rm messages.yaml

echo "... with pattern"
print_run 'trubar collect -s test_project -o messages.yaml -p submodule -q'
diff messages.yaml test_project/submodule_messages.yaml
rm messages.yaml

echo
echo "Translate"
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -q'
diff -r -x "*.yaml" -x "*.txt" test_translations si_translations
rm -r test_translations

echo "... with pattern"
mkdir test_translations
cp test_project/__init__.py test_translations/__init__.py
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -p submodule -q'
diff -r test_translations/submodule si_translations/submodule
diff test_translations/__init__.py test_project/__init__.py
rm -r test_translations

echo "... dry run"
cp -r test_project test_translations
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -q -n'
diff -r test_project test_translations
rm -r test_translations


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
echo "Done."
)

cd - > /dev/null