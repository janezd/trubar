echo "Merge"

cp translations.yaml tmp/translations-copy.yaml
print_run 'trubar merge new_translations.jaml translations.yaml -o tmp/updated_translations.yaml'
diff translations.yaml tmp/translations-copy.yaml
diff tmp/updated_translations.yaml exp/updated_translations.yaml
rm tmp/updated_translations.yaml
print_run 'trubar merge new_translations.jaml translations.yaml -o tmp/updated_translations.jaml'
diff translations.yaml tmp/translations-copy.yaml
diff tmp/updated_translations.jaml exp/updated_translations.jaml
rm tmp/updated_translations.jaml

echo "... in place"
cp translations.yaml tmp/translations.yaml
print_run 'trubar merge new_translations.jaml tmp/translations.yaml'
diff tmp/translations.yaml exp/updated_translations.yaml
rm tmp/translations.yaml

echo "... with pattern"
print_run 'trubar merge new_translations.jaml translations.yaml -o updated_translations.jaml -p submodule'
diff updated_translations.jaml exp/updated_translations_submodule.jaml
rm updated_translations.jaml

echo "... with errors"
cp translations.yaml tmp/translations-copy.yaml
print_run 'trubar merge faulty_translations.yaml tmp/translations-copy.yaml -o tmp/updated_translations.yaml -u tmp/unused.yaml' tmp/errors.txt
diff tmp/translations-copy.yaml translations.yaml
diff tmp/updated_translations.yaml exp/updated_translations_faulty.yaml
diff tmp/unused.yaml exp/unused.yaml
if [[ ! -z $(cat tmp/errors.txt) ]]
then
    echo "merge mustn't output unused items when writing them to a file"
    cat tmp/errors.txt
    exit 1
fi
rm tmp/updated_translations.yaml tmp/unused.yaml tmp/errors.txt

echo "... dry-run, with errors"
print_run 'trubar merge faulty_translations.yaml tmp/translations-copy.yaml -u tmp/unused.yaml -n' tmp/errors.txt
diff tmp/translations-copy.yaml translations.yaml
diff tmp/unused.yaml exp/unused.yaml
if [[ ! -z $(cat tmp/errors.txt) ]]
then
    echo "merge mustn't output unused items when writing them to a file"
    cat tmp/errors.txt
    exit 1
fi
rm tmp/unused.yaml tmp/errors.txt

echo "... dry-run, with errors"
print_run 'trubar merge faulty_translations.yaml tmp/translations-copy.yaml -n' tmp/errors.txt
diff tmp/translations-copy.yaml translations.yaml
diff tmp/errors.txt tmp/errors.txt
rm  tmp/translations-copy.yaml tmp/errors.txt
