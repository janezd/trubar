function print_run() {
    echo "> " $1
    ${1}
}

cd trubar/tests

(
set -e
echo "Collection"
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

echo "Collection with pattern"
print_run 'trubar collect -s test_project -o messages.yaml -p submodule -q'
diff messages.yaml test_project/submodule_messages.yaml
rm messages.yaml

echo "Translation"
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -q'
diff -r -x "*.yaml" test_translations si_translations
rm -r test_translations

echo "Translation with pattern"
mkdir test_translations
cp test_project/__init__.py test_translations/__init__.py
print_run 'trubar translate -s test_project -d test_translations test_project/translations.yaml -p submodule -q'
diff test_translations/__init__.py test_project/__init__.py
diff test_translations/submodule/apples.py si_translations/submodule/apples.py
rm -r test_translations

echo "Update"
cp test_project/translations.yaml translations-copy.yaml
print_run 'trubar update test_project/new_translations.yaml test_project/translations.yaml -o updated_translations.yaml'
diff test_project/translations.yaml translations-copy.yaml
diff updated_translations.yaml test_project/updated_translations.yaml
rm updated_translations.yaml

echo "Update in place"
cp test_project/translations.yaml translations-copy.yaml
print_run 'trubar update test_project/new_translations.yaml test_project/translations.yaml'
diff test_project/translations.yaml test_project/updated_translations.yaml
mv translations-copy.yaml test_project/translations.yaml

echo "Update with pattern"
print_run 'trubar update test_project/new_translations.yaml test_project/translations.yaml -o updated_translations.yaml -p submodule'
diff updated_translations.yaml test_project/updated_translations_submodule.yaml
rm updated_translations.yaml

echo "Extract missing translations (all missing)"
print_run 'trubar missing test_project/all_messages.yaml -o missing.yaml'
diff missing.yaml test_project/all_messages.yaml
rm missing.yaml

echo "Extract missing translations (some missing)"
print_run 'trubar missing test_project/translations.yaml -o missing.yaml'
diff missing.yaml test_project/missing.yaml
rm missing.yaml

echo "Extract missing translations (some missing, pattern)"
print_run 'trubar missing test_project/translations.yaml -o missing.yaml -p trash'
diff missing.yaml test_project/missing_trash.yaml
rm missing.yaml

echo "Extract missing translations (given all messages)"
echo "Extract missing translations (given all messages)"
print_run 'trubar missing test_project/translations.yaml  -m test_project/all_messages.yaml -o missing.yaml'
diff missing.yaml test_project/missing.yaml
rm missing.yaml

echo "Extract missing translations (given all messages and pattern)"
print_run 'trubar missing test_project/translations.yaml  -m test_project/all_messages.yaml -o missing.yaml -p trash'
diff missing.yaml test_project/missing_trash.yaml
rm missing.yaml

echo "Create template from existing translations"
print_run 'trubar template test_project/translations_for_template.yaml -o template.yaml'
diff template.yaml test_project/template.yaml
rm template.yaml

echo "Done."
)

cd - > /dev/null