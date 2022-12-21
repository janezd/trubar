echo "Collect"

print_run 'trubar collect -s ../test_project -o tmp/messages.yaml -q'
diff tmp/messages.yaml exp/all_messages.yaml
if [ -n "`trubar collect -s ../test_project -o tmp/messages.yaml -q`" ]
then
  echo "Not quiet."
  exit 1
fi
if [ -z "`trubar collect -s ../test_project -o tmp/messages.yaml`" ]
then
  echo "Not loud."
  exit 1
fi
rm tmp/messages.yaml

echo "... with pattern"
print_run 'trubar collect -s ../test_project -o tmp/messages.yaml -p submodule -q'
diff tmp/messages.yaml exp/submodule_messages.yaml
rm tmp/messages.yaml

echo "... invalid source dir"
set +e
print_run 'trubar collect -s ../test_project/__init__.py -o tmp/messages.yaml -q' /dev/null
if [ $? -eq 0 ]
then
    echo "Non-zero exit code expected"
    exit 1
fi
print_run 'trubar collect -s ../test_project_not -o tmp/messages.yaml -q' /dev/null
if [ $? -eq 0 ]
then
    echo "Non-zero exit code expected"
    exit 1
fi
