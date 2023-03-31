echo "(Utils)"

echo "... checks for file sanity"
set +e
print_run 'trubar missing bad_structure.yaml -o tmp/missing.yaml' tmp/errors_structure.txt
check_exit_code
set -e
diff tmp/errors_structure.txt exp/errors_structure.txt
rm tmp/errors_structure.txt