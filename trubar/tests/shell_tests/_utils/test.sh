echo "(Utils)"

echo "... checks for file sanity"
set +e
print_run 'trubar missing bad_structure.yaml -o tmp/missing.yaml' tmp/errors_structure.txt
if [ $? -eq 0 ]
then
    echo "Non-zero exit code expected"
    exit 1
fi
set -e
diff tmp/errors_structure.txt exp/errors_structure.txt
rm tmp/errors_structure.txt