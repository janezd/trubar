# to be run from trubar/tests/shell_test_files

echo "Missing"
echo "... all missing"
print_run 'trubar missing all_messages.yaml -o tmp/missing.yaml'
diff tmp/missing.yaml all_messages.yaml
rm tmp/missing.yaml

echo "... some missing"
print_run 'trubar missing translations.jaml -o tmp/missing.jaml'
diff tmp/missing.jaml exp/missing.jaml
rm tmp/missing.jaml

echo "... some missing, pattern"
print_run 'trubar missing translations.jaml -o tmp/missing.jaml -p trash'
diff tmp/missing.jaml exp/missing_trash.jaml
rm tmp/missing.jaml

echo "... given all messages"
print_run 'trubar missing translations.jaml  -m all_messages.yaml -o tmp/missing.jaml'
diff tmp/missing.jaml exp/missing.jaml
rm tmp/missing.jaml

echo "... given all messages and pattern"
print_run 'trubar missing translations.jaml  -m all_messages.yaml -o tmp/missing.jaml -p trash'
diff tmp/missing.jaml exp/missing_trash.jaml
rm tmp/missing.jaml
