echo "Collect"

print_run 'trubar collect -s ../test_project tmp/messages.yaml -q'
diff tmp/messages.yaml exp/all_messages.yaml
if [ -n "`trubar collect -s ../test_project tmp/messages.yaml -q`" ]
then
  echo "Not quiet."
  exit 1
fi
if [ -z "`trubar collect -s ../test_project tmp/messages.yaml`" ]
then
  echo "Not loud."
  exit 1
fi
rm tmp/messages.yaml

echo "... with pattern"
print_run 'trubar collect -s ../test_project tmp/messages.yaml -p submodule -q'
diff tmp/messages.yaml exp/submodule_messages.yaml
rm tmp/messages.yaml

echo "... merge with existing file"
cp some_messages.yaml tmp/some_messages.yaml
print_run 'trubar collect -s ../test_project -r tmp/removed.yaml tmp/some_messages.yaml -q'
diff tmp/some_messages.yaml exp/merged_messages.yaml
diff tmp/removed.yaml exp/removed.yaml
rm tmp/some_messages.yaml tmp/removed.yaml

echo "... merge with existing file, default removed file"
cp some_messages.yaml tmp/some_messages.yaml
print_run 'trubar collect -s ../test_project tmp/some_messages.yaml -q'
diff tmp/some_messages.yaml exp/merged_messages.yaml
diff tmp/removed-from-some_messages.yaml exp/removed.yaml
rm tmp/some_messages.yaml tmp/removed-from-some_messages.yaml

echo "... merge with existing file, with pattern"
cp some_messages.yaml tmp/some_messages.yaml
print_run 'trubar collect -s ../test_project -r tmp/removed.yaml -p submodule tmp/some_messages.yaml -q'
diff tmp/some_messages.yaml exp/merged_messages_pattern.yaml
diff tmp/removed.yaml exp/removed_pattern.yaml
rm tmp/some_messages.yaml tmp/removed.yaml

echo "... merge with existing file, dry run"
cp some_messages.yaml tmp/some_messages.yaml
print_run 'trubar collect -s ../test_project -r tmp/removed.yaml -n -q tmp/some_messages.yaml'
diff tmp/some_messages.yaml some_messages.yaml
diff tmp/removed.yaml exp/removed.yaml
rm tmp/some_messages.yaml tmp/removed.yaml

echo "... merge with existing file, dry run, default removed file"
cp some_messages.yaml tmp/some_messages.yaml
print_run 'trubar collect -s ../test_project tmp/some_messages.yaml -n -q' tmp/removed_output
diff tmp/some_messages.yaml some_messages.yaml
diff tmp/removed-from-some_messages.yaml exp/removed.yaml
rm tmp/some_messages.yaml tmp/removed-from-some_messages.yaml

echo "... invalid source dir"
set +e
print_run 'trubar collect -s ../test_project/__init__.py tmp/messages.yaml -q' /dev/null
check_exit_code
print_run 'trubar collect -s ../test_project_not tmp/messages.yaml -q' /dev/null
check_exit_code
set -e

set +e
echo "... invalid source dir correction"
cp some_messages.yaml tmp/some_messages.yaml
print_run 'trubar collect -s .. tmp/some_messages.yaml' tmp/output.txt
check_exit_code
grep -q "instead" tmp/output.txt
check_exit_code "No error message" -ne
set -e
rm tmp/some_messages.yaml tmp/output.txt
